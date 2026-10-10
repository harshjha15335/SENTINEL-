"""Order creation and capture. The server decides the amount; the client never does."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models import Product, Transaction
from app.models.enums import TransactionStatus
from app.services import audit
from app.services.paypal.gateway import PayPalGateway
from app.services.paypal.types import CreateOrderInput, LineItem, Money, PayPalError
from app.services.risk.scoring import score_after_capture

log = logging.getLogger("sentinel.checkout")

MAX_QUANTITY = 10


class PaymentProviderError(DomainError):
    status_code = 502
    code = "payment_provider_error"


def _provider_error(exc: PayPalError) -> PaymentProviderError:
    return PaymentProviderError(
        exc.message,
        details={"kind": exc.kind.value, "issue": exc.issue, "debug_id": exc.debug_id},
    )


def create_order(
    db: Session,
    gateway: PayPalGateway,
    principal: Principal,
    *,
    product_id: uuid.UUID,
    quantity: int,
    idempotency_key: str,
) -> Transaction:
    if not 1 <= quantity <= MAX_QUANTITY:
        raise DomainError(f"Quantity must be between 1 and {MAX_QUANTITY}")

    existing = db.scalar(
        select(Transaction).where(
            Transaction.merchant_id == principal.merchant_id,
            Transaction.create_idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.product_id != product_id or existing.quantity != quantity:
            raise ConflictError("Idempotency key was already used for a different order")
        return existing

    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.merchant_id == principal.merchant_id,
            Product.active.is_(True),
        )
    )
    if product is None:
        raise NotFoundError("Product not found")

    unit = Money(product.price_minor, product.currency)
    txn = Transaction(
        merchant_id=principal.merchant_id,
        product_id=product.id,
        created_by_user_id=principal.user.id,
        quantity=quantity,
        amount_minor=unit.amount_minor * quantity,
        currency=unit.currency,
        status=TransactionStatus.ORDER_CREATED,
        create_idempotency_key=idempotency_key,
        paypal_request_id=f"sentinel-create-{uuid.uuid4()}",
        data_origin=gateway.data_origin,
        provider_summary={},
    )
    db.add(txn)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Concurrent request with the same idempotency key") from exc

    try:
        result = gateway.create_order(
            CreateOrderInput(
                reference_id=str(txn.id),
                request_id=txn.paypal_request_id,
                description=f"SENTINEL demo: {product.name}"[:127],
                items=[LineItem(product.name[:127], product.sku, quantity, unit)],
            )
        )
    except PayPalError as exc:
        db.rollback()
        raise _provider_error(exc) from exc

    txn.paypal_order_id = result.order_id
    txn.provider_status = result.status
    txn.provider_summary = {"create": result.summary}
    audit.record(
        db,
        action="paypal.order.created",
        entity_type="transaction",
        entity_id=txn.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
        metadata={
            "paypal_order_id": result.order_id,
            "amount_minor": txn.amount_minor,
            "currency": txn.currency,
            "gateway": gateway.name,
        },
    )
    db.commit()
    return txn


def capture_order(
    db: Session, gateway: PayPalGateway, principal: Principal, *, paypal_order_id: str
) -> Transaction:
    txn = db.scalar(
        select(Transaction)
        .where(
            Transaction.paypal_order_id == paypal_order_id,
            Transaction.merchant_id == principal.merchant_id,
        )
        .with_for_update(of=Transaction)
    )
    if txn is None:
        raise NotFoundError("Order not found")
    if txn.status in (
        TransactionStatus.CAPTURED,
        TransactionStatus.REFUNDED,
        TransactionStatus.PARTIALLY_REFUNDED,
    ):
        db.rollback()
        return txn  # Already captured: idempotent success, no second provider call.

    try:
        # Deterministic request id: a retried capture can never double-capture at PayPal.
        result = gateway.capture_order(paypal_order_id, request_id=f"sentinel-capture-{txn.id}")
    except PayPalError as exc:
        txn.status = TransactionStatus.CAPTURE_FAILED
        txn.failure_reason = f"{exc.kind.value}: {exc.issue or exc.message}"
        audit.record(
            db,
            action="paypal.order.capture_failed",
            entity_type="transaction",
            entity_id=txn.id,
            merchant_id=principal.merchant_id,
            actor_id=principal.user.id,
            metadata={"kind": exc.kind.value, "issue": exc.issue, "debug_id": exc.debug_id},
        )
        db.commit()
        raise _provider_error(exc) from exc

    expected = Money(txn.amount_minor, txn.currency)
    txn.provider_status = result.capture_status or result.order_status
    txn.paypal_capture_id = result.capture_id
    txn.payer_reference = result.payer_id
    txn.provider_summary = {**txn.provider_summary, "capture": result.summary}
    txn.occurred_at = _parse_time(result.create_time) or datetime.now(UTC)

    if result.amount is not None and result.amount != expected:
        # Never trust a mismatch silently; flag it for review rather than marking it captured.
        txn.status = TransactionStatus.CAPTURE_FAILED
        txn.failure_reason = f"Captured amount {result.amount} differs from expected {expected}"
    elif result.capture_status == "COMPLETED":
        txn.status = TransactionStatus.CAPTURED
        txn.failure_reason = None
    elif result.capture_status == "PENDING":
        txn.status = TransactionStatus.CAPTURE_PENDING
    elif result.capture_status == "DECLINED":
        txn.status = TransactionStatus.CAPTURE_DECLINED
    else:
        txn.status = TransactionStatus.CAPTURE_FAILED
        txn.failure_reason = f"Unexpected capture status {result.capture_status!r}"

    audit.record(
        db,
        action="paypal.order.captured",
        entity_type="transaction",
        entity_id=txn.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
        metadata={
            "paypal_order_id": paypal_order_id,
            "paypal_capture_id": result.capture_id,
            "capture_status": result.capture_status,
            "result_status": txn.status.value,
            "gateway": gateway.name,
        },
    )
    db.commit()
    if txn.status in (TransactionStatus.CAPTURED, TransactionStatus.CAPTURE_PENDING):
        # Decision support only: the capture has already happened and is never undone here.
        score_after_capture(db, txn.id)
    return txn


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
