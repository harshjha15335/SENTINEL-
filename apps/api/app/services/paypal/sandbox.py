"""Real PayPal sandbox gateway using documented REST endpoints over HTTPX.

Why REST rather than paypal-server-sdk: the official Server SDK (2.4.0) covers Orders,
Payments, Vault, Transaction Search and Subscriptions, but not Disputes or webhook
signature verification. Using one documented HTTP client for every PayPal call keeps
error classification, idempotency headers, timeouts and logging uniform.
See docs/decisions/0002-paypal-rest-over-sdk.md.
"""

import logging
import threading
import time
from typing import Any

import httpx

from app.models.enums import DataOrigin
from app.services.paypal.parsing import parse_capture, parse_order
from app.services.paypal.types import (
    CaptureResult,
    CreateOrderInput,
    Money,
    OrderResult,
    PayPalError,
    PayPalErrorKind,
    RefundResult,
)

log = logging.getLogger("sentinel.paypal")

# Sandbox only. There is intentionally no configuration path to the live host.
SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"
_TOKEN_REFRESH_MARGIN_SECONDS = 120


class SandboxPayPalGateway:
    data_origin = DataOrigin.LIVE_SANDBOX
    name = "sandbox"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 2,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.Client(base_url=SANDBOX_BASE_URL, timeout=timeout, transport=transport)
        self._max_retries = max_retries
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    # ---- auth -----------------------------------------------------------------------------

    def _access_token(self, *, force: bool = False) -> str:
        with self._lock:
            now = time.monotonic()
            if not force and self._token and now < self._token_expires_at:
                return self._token
            try:
                resp = self._http.post(
                    "/v1/oauth2/token",
                    data={"grant_type": "client_credentials"},
                    auth=(self._client_id, self._client_secret),
                    headers={"Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise PayPalError(
                    PayPalErrorKind.NETWORK, f"Token request failed: {type(exc).__name__}"
                ) from exc
            if resp.status_code != 200:
                raise _classify(resp, "OAuth2 token request rejected")
            body = resp.json()
            self._token = str(body["access_token"])
            ttl = int(body.get("expires_in", 0))
            self._token_expires_at = now + max(ttl - _TOKEN_REFRESH_MARGIN_SECONDS, 30)
            log.info("paypal token acquired", extra={"data": {"expires_in": ttl}})
            return self._token

    def check_credentials(self) -> None:
        self._access_token()

    # ---- transport ------------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        prefer_representation: bool = True,
    ) -> dict[str, Any]:
        refreshed = False
        attempt = 0
        while True:
            headers = {
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if prefer_representation:
                headers["Prefer"] = "return=representation"
            if request_id:
                # PayPal's idempotency header: retries with the same id return the original result.
                headers["PayPal-Request-Id"] = request_id
            try:
                resp = self._http.request(method, path, json=json, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                err = PayPalError(PayPalErrorKind.NETWORK, f"Timeout calling PayPal {path}")
                if request_id and attempt < self._max_retries:
                    attempt += 1
                    time.sleep(0.5 * attempt)
                    continue
                raise err from exc
            except httpx.HTTPError as exc:
                raise PayPalError(
                    PayPalErrorKind.NETWORK, f"Network error: {type(exc).__name__}"
                ) from exc

            if resp.status_code == 401 and not refreshed:
                refreshed = True
                self._access_token(force=True)
                continue
            if (
                resp.status_code in (429, 500, 502, 503, 504)
                and request_id
                and attempt < self._max_retries
            ):
                # Only retried when an idempotency key guarantees no duplicate side effect.
                attempt += 1
                time.sleep(0.5 * attempt)
                continue
            if resp.status_code >= 400:
                raise _classify(resp, f"PayPal {method} {path} failed")
            log.info(
                "paypal call",
                extra={
                    "data": {
                        "method": method,
                        "path": path,
                        "status": resp.status_code,
                        "debug_id": resp.headers.get("paypal-debug-id"),
                    }
                },
            )
            if not resp.content:
                return {}
            data: dict[str, Any] = resp.json()
            return data

    # ---- Orders v2 ------------------------------------------------------------------------

    def create_order(self, order: CreateOrderInput) -> OrderResult:
        total = order.total
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": order.reference_id,
                    "custom_id": order.reference_id,
                    "description": order.description,
                    "amount": {
                        "currency_code": total.currency,
                        "value": total.to_paypal_value(),
                        "breakdown": {
                            "item_total": {
                                "currency_code": total.currency,
                                "value": total.to_paypal_value(),
                            }
                        },
                    },
                    "items": [
                        {
                            "name": item.name,
                            "sku": item.sku,
                            "quantity": str(item.quantity),
                            "unit_amount": {
                                "currency_code": item.unit_amount.currency,
                                "value": item.unit_amount.to_paypal_value(),
                            },
                            "category": "DIGITAL_GOODS",
                        }
                        for item in order.items
                    ],
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                    }
                }
            },
        }
        data = self._request("POST", "/v2/checkout/orders", json=body, request_id=order.request_id)
        return parse_order(data)

    def capture_order(self, order_id: str, *, request_id: str) -> CaptureResult:
        data = self._request(
            "POST",
            f"/v2/checkout/orders/{_safe_id(order_id)}/capture",
            json={},
            request_id=request_id,
        )
        return parse_capture(order_id, data)

    def get_order(self, order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/checkout/orders/{_safe_id(order_id)}")

    # ---- Payments v2 ----------------------------------------------------------------------

    def get_capture(self, capture_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/payments/captures/{_safe_id(capture_id)}")

    def refund_capture(
        self, capture_id: str, *, amount: Money | None, request_id: str, note: str | None
    ) -> RefundResult:
        body: dict[str, Any] = {}
        if amount is not None:
            body["amount"] = {"currency_code": amount.currency, "value": amount.to_paypal_value()}
        if note:
            body["note_to_payer"] = note[:255]
        data = self._request(
            "POST",
            f"/v2/payments/captures/{_safe_id(capture_id)}/refund",
            json=body,
            request_id=request_id,
        )
        refunded = None
        if data.get("amount"):
            refunded = Money.from_paypal(data["amount"]["value"], data["amount"]["currency_code"])
        return RefundResult(
            refund_id=str(data["id"]),
            status=str(data.get("status", "UNKNOWN")),
            amount=refunded,
            summary={
                "id": data.get("id"),
                "status": data.get("status"),
                "amount": data.get("amount"),
            },
        )

    # ---- Disputes v1 (account-permission dependent) ---------------------------------------

    def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/customer/disputes/{_safe_id(dispute_id)}", prefer_representation=False
        )

    def list_disputes(self, *, page_size: int = 20) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/customer/disputes",
            params={"page_size": max(1, min(page_size, 50))},
            prefer_representation=False,
        )


def _safe_id(value: str) -> str:
    """PayPal resource ids are alphanumeric with dashes; refuse anything else (path injection)."""
    if not value or len(value) > 64 or not all(c.isalnum() or c in "-_" for c in value):
        raise PayPalError(PayPalErrorKind.VALIDATION, "Invalid PayPal resource id")
    return value


def _classify(resp: httpx.Response, fallback: str) -> PayPalError:
    debug_id = resp.headers.get("paypal-debug-id")
    issue: str | None = None
    message = fallback
    try:
        body = resp.json()
        details = body.get("details") or []
        if details:
            issue = details[0].get("issue")
        message = body.get("message") or body.get("error_description") or fallback
    except ValueError:
        pass
    status = resp.status_code
    if status == 401:
        kind = PayPalErrorKind.AUTHENTICATION
    elif status == 403:
        kind = PayPalErrorKind.PERMISSION
    elif status == 400:
        kind = PayPalErrorKind.VALIDATION
    elif status == 404:
        kind = PayPalErrorKind.NOT_FOUND
    elif status == 409:
        kind = PayPalErrorKind.CONFLICT
    elif status == 422:
        kind = PayPalErrorKind.UNPROCESSABLE
    elif status == 429:
        kind = PayPalErrorKind.RATE_LIMITED
    else:
        kind = PayPalErrorKind.PROVIDER_ERROR
    log.warning(
        "paypal error",
        extra={"data": {"status": status, "kind": kind, "issue": issue, "debug_id": debug_id}},
    )
    return PayPalError(kind, message, status_code=status, debug_id=debug_id, issue=issue)
