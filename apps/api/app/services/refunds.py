"""Approval-protected sandbox refunds with no automatic retries after submission.

An ambiguous provider result reserves its amount until a known refund ID can be reconciled.
A crash after the durable EXECUTING transition never triggers automatic re-submission.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.config import get_settings
from app.core.errors import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from app.models import Transaction
from app.models.enums import DataOrigin, Role, TransactionStatus
from app.models.refunds import RefundRequest
from app.services import audit
from app.services.approvals import snapshot_digest
from app.services.cases import get_case
from app.services.paypal.gateway import PayPalGateway
from app.services.paypal.types import Money, PayPalError, PayPalErrorKind, RefundResult

RESERVED = ("PENDING_APPROVAL", "APPROVED", "EXECUTING", "SUCCEEDED", "RECONCILIATION_REQUIRED")
LIMITATION = (
    "Execution is disabled by default and sandbox-only. Available amount uses the managed "
    "ledger; ambiguous or externally refunded payments require reconciliation. "
    "Approval is not provider confirmation."
)


class InvalidRefund(DomainError):
    code = "invalid_refund"
    status_code = 422


def enabled() -> bool:
    settings = get_settings()
    return (
        bool(getattr(settings, "refund_execution_enabled", False))
        and settings.environment != "production"
    )


def _admin(principal: Principal) -> None:
    if principal.role is not Role.ADMIN:
        raise PermissionDeniedError("Administrator confirmation required")


def _operator(principal: Principal) -> None:
    if principal.role not in (Role.ADMIN, Role.ANALYST):
        raise PermissionDeniedError("Your role cannot request a refund")


def transaction(
    db: Session, merchant_id: uuid.UUID, transaction_id: uuid.UUID, *, lock: bool = False
) -> Transaction:
    stmt = select(Transaction).where(
        Transaction.id == transaction_id, Transaction.merchant_id == merchant_id
    )
    if lock:
        stmt = stmt.with_for_update(of=Transaction).execution_options(populate_existing=True)
    txn = db.scalar(stmt)
    if txn is None:
        raise NotFoundError("Payment not found")
    return txn


def reserved_amount(db: Session, txn: Transaction, *, exclude: uuid.UUID | None = None) -> int:
    stmt = select(func.coalesce(func.sum(RefundRequest.amount_minor), 0)).where(
        RefundRequest.transaction_id == txn.id, RefundRequest.status.in_(RESERVED)
    )
    if exclude:
        stmt = stmt.where(RefundRequest.id != exclude)
    return int(db.scalar(stmt) or 0)


def balance_known(db: Session, txn: Transaction) -> bool:
    succeeded, last = db.execute(
        select(
            func.coalesce(func.sum(RefundRequest.amount_minor), 0),
            func.max(RefundRequest.completed_at),
        ).where(RefundRequest.transaction_id == txn.id, RefundRequest.status == "SUCCEEDED")
    ).one()
    if txn.status is TransactionStatus.PARTIALLY_REFUNDED:
        return bool(succeeded and last and txn.refunded_at == last)
    if txn.status is TransactionStatus.REFUNDED:
        return bool(succeeded == txn.amount_minor and last and txn.refunded_at == last)
    return txn.status is TransactionStatus.CAPTURED and txn.refunded_at is None


def _eligible(db: Session, txn: Transaction) -> None:
    if txn.status not in (TransactionStatus.CAPTURED, TransactionStatus.PARTIALLY_REFUNDED):
        raise ConflictError("Only captured or managed partially refunded payments are eligible")
    if not balance_known(db, txn):
        raise ConflictError("External refund balance is unknown; reconcile before creating refunds")


def get(
    db: Session, merchant_id: uuid.UUID, refund_id: uuid.UUID, *, lock: bool = False
) -> RefundRequest:
    stmt = select(RefundRequest).where(
        RefundRequest.id == refund_id, RefundRequest.merchant_id == merchant_id
    )
    if lock:
        stmt = stmt.with_for_update(of=RefundRequest).execution_options(populate_existing=True)
    refund = db.scalar(stmt)
    if refund is None:
        raise NotFoundError("Refund request not found")
    return refund


def _record(db: Session, refund: RefundRequest, principal: Principal, action: str) -> None:
    case = get_case(db, principal.merchant_id, refund.case_id)
    audit.record_for_case(
        db,
        case,
        action,
        principal.user.id,
        entity_type="refund_request",
        entity_id=refund.id,
        status=refund.status,
        amount_minor=refund.amount_minor,
        currency=refund.currency,
        snapshot_sha256=refund.snapshot_sha256,
        submission_started=refund.submission_started,
    )


def create(
    db: Session, principal: Principal, case_id: uuid.UUID, *, amount_minor: int | None
) -> RefundRequest:
    _operator(principal)
    case = get_case(db, principal.merchant_id, case_id)
    txn = transaction(db, principal.merchant_id, case.transaction_id, lock=True)
    used = reserved_amount(db, txn)
    _eligible(db, txn)
    available = txn.amount_minor - used
    requested = available if amount_minor is None else amount_minor
    if isinstance(requested, bool) or requested <= 0 or requested > available:
        raise InvalidRefund(
            "Refund must be positive and cannot exceed the unreserved captured balance"
        )
    identity = uuid.uuid4()
    snapshot = {
        "case_id": str(case.id),
        "transaction_id": str(txn.id),
        "amount_minor": requested,
        "captured_amount_minor": txn.amount_minor,
        "currency": txn.currency,
        "paypal_capture_id": txn.paypal_capture_id,
        "data_origin": txn.data_origin.value,
    }
    refund = RefundRequest(
        id=identity,
        merchant_id=txn.merchant_id,
        case_id=case.id,
        transaction_id=txn.id,
        amount_minor=requested,
        currency=txn.currency,
        data_origin=txn.data_origin.value,
        requested_by_user_id=principal.user.id,
        status="PENDING_APPROVAL",
        snapshot=snapshot,
        snapshot_sha256=snapshot_digest(snapshot),
        request_key="sentinel-refund-" + str(identity),
    )
    db.add(refund)
    db.flush()
    _record(db, refund, principal, "refund.requested")
    db.commit()
    return refund


def _verify_snapshot(refund: RefundRequest, txn: Transaction, digest: str) -> None:
    if (
        snapshot_digest(refund.snapshot) != refund.snapshot_sha256
        or digest != refund.snapshot_sha256
    ):
        raise ConflictError("Refund snapshot does not match the confirmed request")
    s = refund.snapshot
    if any(
        (
            s.get("transaction_id") != str(txn.id),
            s.get("amount_minor") != refund.amount_minor,
            s.get("currency") != txn.currency,
            s.get("captured_amount_minor") != txn.amount_minor,
            s.get("paypal_capture_id") != txn.paypal_capture_id,
            s.get("data_origin") != txn.data_origin.value,
        )
    ):
        raise ConflictError("The payment no longer matches the approved snapshot")


def decide(
    db: Session, principal: Principal, refund_id: uuid.UUID, *, decision: str, digest: str
) -> RefundRequest:
    _admin(principal)
    initial = get(db, principal.merchant_id, refund_id)
    txn = transaction(db, principal.merchant_id, initial.transaction_id, lock=True)
    refund = get(db, principal.merchant_id, refund_id, lock=True)
    if refund.status != "PENDING_APPROVAL":
        raise ConflictError("This refund request has already been decided")
    if refund.requested_by_user_id == principal.user.id:
        raise PermissionDeniedError("You cannot approve or reject your own refund request")
    if decision not in ("APPROVED", "REJECTED"):
        raise InvalidRefund("Choose APPROVED or REJECTED")
    _verify_snapshot(refund, txn, digest)
    refund.status, refund.decided_by_user_id, refund.decided_at = (
        decision,
        principal.user.id,
        datetime.now(UTC),
    )
    refund.decided_by_role = principal.role.value
    _record(db, refund, principal, "refund." + decision.lower())
    db.commit()
    return refund


def _apply_result(
    db: Session, refund: RefundRequest, txn: Transaction, result: RefundResult
) -> None:
    refund.provider_refund_id, refund.provider_status = result.refund_id, result.status
    if not result.amount or result.amount != Money(refund.amount_minor, refund.currency):
        refund.status, refund.error_category = "RECONCILIATION_REQUIRED", "AMOUNT_MISMATCH"
        return
    if result.status == "COMPLETED":
        refund.status, refund.completed_at, refund.error_category = (
            "SUCCEEDED",
            datetime.now(UTC),
            None,
        )
        db.flush()
        refunded = (
            db.scalar(
                select(func.coalesce(func.sum(RefundRequest.amount_minor), 0)).where(
                    RefundRequest.transaction_id == txn.id, RefundRequest.status == "SUCCEEDED"
                )
            )
            or 0
        )
        txn.status = (
            TransactionStatus.REFUNDED
            if refunded >= txn.amount_minor
            else TransactionStatus.PARTIALLY_REFUNDED
        )
        txn.refunded_at = refund.completed_at
    elif result.status in ("FAILED", "CANCELLED", "DENIED"):
        refund.status, refund.error_category = "FAILED", "PROVIDER_" + result.status
    else:
        refund.status, refund.error_category = "RECONCILIATION_REQUIRED", "PROVIDER_PENDING"


def execute(
    db: Session, principal: Principal, refund_id: uuid.UUID, *, digest: str, gateway: PayPalGateway
) -> RefundRequest:
    _admin(principal)
    if not enabled():
        raise PermissionDeniedError(
            "Sandbox refund execution is disabled; separate enablement is required"
        )
    initial = get(db, principal.merchant_id, refund_id)
    txn = transaction(db, principal.merchant_id, initial.transaction_id, lock=True)
    refund = get(db, principal.merchant_id, refund_id, lock=True)
    if refund.status == "SUCCEEDED":
        return refund
    if refund.status != "APPROVED" or refund.decided_by_user_id is None:
        raise ConflictError(
            "Only an independently approved refund can be executed; "
            "ambiguous requests are never resubmitted"
        )
    _verify_snapshot(refund, txn, digest)
    if (
        gateway.name != "sandbox"
        or gateway.data_origin is not DataOrigin.LIVE_SANDBOX
        or txn.data_origin is not DataOrigin.LIVE_SANDBOX
        or not txn.paypal_capture_id
    ):
        raise PermissionDeniedError(
            "Execution requires a genuine sandbox capture and sandbox gateway"
        )
    used = reserved_amount(db, txn, exclude=refund.id)
    _eligible(db, txn)
    if used + refund.amount_minor > txn.amount_minor:
        raise ConflictError("Refund balance changed; independent review is required")
    # Refuse invalid IDs before any HTTP call; the gateway validates them as well.
    import re

    if not re.fullmatch(r"[A-Z0-9]{10,32}", txn.paypal_capture_id):
        raise InvalidRefund("PayPal capture identifier is invalid")
    # A nonfinancial capture lookup validates the current mapping and original currency/amount.
    # Refund totals not represented by local synchronized events remain a documented limitation.
    capture = gateway.get_capture(txn.paypal_capture_id)
    try:
        capture_amount = Money.from_paypal(
            capture["amount"]["value"], capture["amount"]["currency_code"]
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ConflictError("Capture amount is unavailable; no refund submitted") from exc
    if capture.get("id") != txn.paypal_capture_id or capture_amount != Money(
        txn.amount_minor, txn.currency
    ):
        raise ConflictError("Provider capture does not match the approved payment")
    if capture.get("status") == "PARTIALLY_REFUNDED" and txn.status is TransactionStatus.CAPTURED:
        raise ConflictError(
            "Provider reports an unsynchronized partial refund; no refund submitted"
        )
    if capture.get("status") not in ("COMPLETED", "PARTIALLY_REFUNDED"):
        raise ConflictError("Provider capture status is not eligible for refund")
    refund.status, refund.execution_started_at = "EXECUTING", datetime.now(UTC)
    refund.submission_started, refund.attempts = True, refund.attempts + 1
    _record(db, refund, principal, "refund.execution_started")
    capture_id, amount, key = (
        txn.paypal_capture_id,
        Money(refund.amount_minor, refund.currency),
        refund.request_key,
    )
    db.commit()  # durable claim precedes the external mutation
    try:
        result = gateway.refund_capture(capture_id, amount=amount, request_id=key, note=None)
    except PayPalError as exc:
        refund = get(db, principal.merchant_id, refund_id, lock=True)
        # Auth/validation rejection explicitly establishes no successful financial result.
        definitive = exc.kind in (
            PayPalErrorKind.AUTHENTICATION,
            PayPalErrorKind.PERMISSION,
            PayPalErrorKind.VALIDATION,
            PayPalErrorKind.UNPROCESSABLE,
            PayPalErrorKind.NOT_FOUND,
        )
        refund.status = "FAILED" if definitive else "RECONCILIATION_REQUIRED"
        refund.error_category = exc.kind.value
    except Exception:
        refund = get(db, principal.merchant_id, refund_id, lock=True)
        refund.status, refund.error_category = (
            "RECONCILIATION_REQUIRED",
            "AMBIGUOUS_PROVIDER_RESULT",
        )
    else:
        txn = transaction(db, principal.merchant_id, initial.transaction_id, lock=True)
        refund = get(db, principal.merchant_id, refund_id, lock=True)
        _apply_result(db, refund, txn, result)
    _record(db, refund, principal, "refund.execution_observed")
    db.commit()
    return refund


def reconcile(
    db: Session, principal: Principal, refund_id: uuid.UUID, *, gateway: PayPalGateway
) -> RefundRequest:
    _admin(principal)
    if not enabled():
        raise PermissionDeniedError("Provider reconciliation requires explicit sandbox enablement")
    initial = get(db, principal.merchant_id, refund_id)
    txn = transaction(db, principal.merchant_id, initial.transaction_id, lock=True)
    refund = get(db, principal.merchant_id, refund_id, lock=True)
    if (
        gateway.name != "sandbox"
        or gateway.data_origin is not DataOrigin.LIVE_SANDBOX
        or txn.data_origin is not DataOrigin.LIVE_SANDBOX
    ):
        raise PermissionDeniedError(
            "Only genuine sandbox records may be reconciled through a provider"
        )
    if refund.status == "EXECUTING":
        refund.status, refund.error_category = "RECONCILIATION_REQUIRED", "EXECUTION_INTERRUPTED"
    if refund.status != "RECONCILIATION_REQUIRED":
        raise ConflictError("This refund does not require reconciliation")
    if not refund.provider_refund_id:
        _record(db, refund, principal, "refund.reconciliation_blocked")
        db.commit()
        raise ConflictError(
            "Provider refund ID is unknown; operator must establish provider outcome. "
            "No resubmission is permitted"
        )

    get_refund = getattr(gateway, "get_refund", None)
    if get_refund is None:
        raise ConflictError("Read-only refund lookup is unavailable for this gateway")
    raw: dict[str, Any] = get_refund(refund.provider_refund_id)
    returned_id = raw.get("id")
    if returned_id != refund.provider_refund_id:
        raise ConflictError("Provider refund ID mismatch")
    parsed = None
    if raw.get("amount"):
        parsed = Money.from_paypal(raw["amount"]["value"], raw["amount"]["currency_code"])
    _apply_result(
        db, refund, txn, RefundResult(str(returned_id), str(raw.get("status", "UNKNOWN")), parsed)
    )
    _record(db, refund, principal, "refund.reconciled")
    db.commit()
    return refund
