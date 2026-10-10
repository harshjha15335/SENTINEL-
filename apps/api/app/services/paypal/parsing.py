"""Pull the fields SENTINEL keeps out of PayPal responses (and nothing more)."""

from typing import Any

from app.services.paypal.types import CaptureResult, Money, OrderResult


def _link(resource: dict[str, Any], rel: str) -> str | None:
    for link in resource.get("links", []) or []:
        if link.get("rel") == rel:
            href = link.get("href")
            return str(href) if href else None
    return None


def parse_order(body: dict[str, Any]) -> OrderResult:
    approve = _link(body, "payer-action") or _link(body, "approve")
    return OrderResult(
        order_id=str(body["id"]),
        status=str(body.get("status", "UNKNOWN")),
        approve_url=approve,
        summary={"id": body.get("id"), "status": body.get("status"), "intent": body.get("intent")},
    )


def parse_capture(order_id: str, body: dict[str, Any]) -> CaptureResult:
    capture: dict[str, Any] = {}
    units = body.get("purchase_units") or []
    if units:
        captures = ((units[0].get("payments") or {}).get("captures")) or []
        if captures:
            capture = captures[0]
    amount = None
    if capture.get("amount"):
        amount = Money.from_paypal(
            str(capture["amount"]["value"]), str(capture["amount"]["currency_code"])
        )
    payer = body.get("payer") or {}
    summary = {
        "order_id": body.get("id", order_id),
        "order_status": body.get("status"),
        "capture_id": capture.get("id"),
        "capture_status": capture.get("status"),
        "status_details": capture.get("status_details"),
        "amount": capture.get("amount"),
        "seller_protection": (capture.get("seller_protection") or {}).get("status"),
        "create_time": capture.get("create_time"),
    }
    return CaptureResult(
        order_id=str(body.get("id", order_id)),
        order_status=str(body.get("status", "UNKNOWN")),
        capture_id=capture.get("id"),
        capture_status=capture.get("status"),
        amount=amount,
        payer_id=payer.get("payer_id"),
        create_time=capture.get("create_time"),
        summary=summary,
    )
