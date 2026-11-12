import html
import re

from fastapi import APIRouter, Depends, Header
from fastapi.responses import HTMLResponse
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
    if settings.paypal_mode is PayPalMode.SANDBOX:
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


_CARD_CSS = (
    "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;"
    " background: #0f172a; color: #f8fafc; display: flex; align-items: center;"
    " justify-content: center; min-height: 100dvh; margin: 0;"
    " padding: 1rem; box-sizing: border-box; }"
    " .card { background: #1e293b; padding: 2rem; border-radius: 0.75rem;"
    " border: 1px solid #334155; max-width: 480px; width: 100%; box-sizing: border-box;"
    " box-shadow: 0 10px 25px rgba(0,0,0,0.5); }"
    " .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px;"
    " font-size: 0.875rem; font-weight: 600; margin-bottom: 1rem; }"
    " h1 { font-size: 1.25rem; margin: 0 0 0.5rem 0; color: #f8fafc; }"
    " p { color: #94a3b8; font-size: 0.875rem; line-height: 1.5; margin: 0 0 1rem 0; }"
    " code { background: #0f172a; color: #38bdf8; padding: 0.2rem 0.4rem;"
    " border-radius: 0.25rem; font-size: 0.8125rem; word-break: break-all; }"
)


@router.get("/return", response_class=HTMLResponse)
def checkout_return(token: str | None = None, PayerID: str | None = None) -> HTMLResponse:
    safe_token = html.escape(token or "—")
    safe_payer = html.escape(PayerID or "—")
    content = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>SENTINEL — PayPal Sandbox Return Received</title>"
        f"<style>{_CARD_CSS} .badge {{ background: #166534; color: #4ade80; }}</style>"
        "</head><body><div class='card'>"
        "<div class='badge'>SANDBOX RETURN RECEIVED</div>"
        "<h1>Approval Not Verified</h1>"
        "<p>A checkout return was received. This page does not verify "
        "buyer approval or payment capture.</p>"
        f"<p>Order Token: <code>{safe_token}</code></p>"
        f"<p>Payer ID: <code>{safe_payer}</code></p>"
        "<p><strong>Next step:</strong> Return to your SENTINEL workspace "
        "to inspect the server-recorded payment status.</p>"
        "</div></body></html>"
    )
    return HTMLResponse(
        content=content,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'"
            ),
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/cancel", response_class=HTMLResponse)
def checkout_cancel(token: str | None = None) -> HTMLResponse:
    safe_token = html.escape(token or "—")
    content = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>SENTINEL — PayPal Sandbox Cancel Return</title>"
        f"<style>{_CARD_CSS} .badge {{ background: #991b1b; color: #f87171; }}</style>"
        "</head><body><div class='card'>"
        "<div class='badge'>SANDBOX CANCEL RETURN</div>"
        "<h1>Checkout Cancel Return</h1>"
        "<p>A checkout cancellation return was received. This page does not "
        "change or verify the payment status.</p>"
        f"<p>Order Token: <code>{safe_token}</code></p>"
        "<p>You may return to your terminal to inspect the recorded transaction status.</p>"
        "</div></body></html>"
    )
    return HTMLResponse(
        content=content,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'"
            ),
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )
