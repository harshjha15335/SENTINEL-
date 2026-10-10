import re

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import paypal_gateway
from app.auth.deps import Principal, any_member, operator
from app.core.config import PayPalMode, get_settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.enums import DataOrigin
from app.schemas.api import CreateOrderRequest, OrderCreatedOut, PayPalStatusOut, TransactionOut
from app.services import checkout
from app.services.paypal.factory import GatewayNotConfigured, get_gateway
from app.services.paypal.gateway import PayPalGateway
from app.services.paypal.types import PayPalError
from app.services.transactions import to_out

router = APIRouter(prefix="/paypal", tags=["paypal"])
_KEY = re.compile(r"^[A-Za-z0-9\-_]{16,128}$")


@router.get("/status", response_model=PayPalStatusOut)
def status(_: Principal = Depends(any_member)) -> PayPalStatusOut:
    settings = get_settings()
    check = "not_attempted"
    token_error: str | None = None
    origin = (
        DataOrigin.SIMULATED
        if settings.paypal_mode is PayPalMode.FIXTURE
        else DataOrigin.LIVE_SANDBOX
    )
    try:
        gateway = get_gateway()
        gateway.check_credentials()
        check = "ok"
    except GatewayNotConfigured as exc:
        token_error = str(exc)
    except PayPalError as exc:
        check = "failed"
        token_error = f"{exc.kind.value}: {exc.message}"
    return PayPalStatusOut(
        mode=settings.paypal_mode.value,
        credentials_configured=settings.paypal_credentials_configured,
        token_check=check,  # type: ignore[arg-type]
        token_error=token_error,
        # The client id is public by design (it is embedded in PayPal's JS SDK URL).
        client_id=settings.paypal_client_id if settings.paypal_mode is PayPalMode.SANDBOX else None,
        webhook_id_configured=bool(settings.paypal_webhook_id),
        data_origin=origin,
    )


@router.post("/orders", response_model=OrderCreatedOut, status_code=201)
def create_order(
    body: CreateOrderRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: Principal = Depends(operator),
    gateway: PayPalGateway = Depends(paypal_gateway),
    db: Session = Depends(get_db),
) -> OrderCreatedOut:
    if not _KEY.match(idempotency_key):
        raise DomainError("Idempotency-Key must be 16-128 URL-safe characters")
    txn = checkout.create_order(
        db,
        gateway,
        principal,
        product_id=body.product_id,
        quantity=body.quantity,
        idempotency_key=idempotency_key,
    )
    assert txn.paypal_order_id
    return OrderCreatedOut(
        transaction_id=txn.id,
        paypal_order_id=txn.paypal_order_id,
        status=txn.status,
        data_origin=txn.data_origin,
    )


@router.post("/orders/{order_id}/capture", response_model=TransactionOut)
def capture_order(
    order_id: str,
    principal: Principal = Depends(operator),
    gateway: PayPalGateway = Depends(paypal_gateway),
    db: Session = Depends(get_db),
) -> TransactionOut:
    txn = checkout.capture_order(db, gateway, principal, paypal_order_id=order_id)
    return to_out(txn)
