"""An httpx MockTransport that imitates the documented PayPal sandbox responses.

Used only by tests that exercise SandboxPayPalGateway's HTTP handling. It is not a
substitute for the sandbox integration test (tests/integration/test_sandbox_live.py).
"""

import json
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class FakePayPal:
    calls: list[httpx.Request] = field(default_factory=list)
    token_calls: int = 0
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_request_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    fail_next: list[int] = field(default_factory=list)
    capture_amount_override: str | None = None
    capture_status: str = "COMPLETED"

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path == "/v1/oauth2/token":
            self.token_calls += 1
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(
                200, json={"access_token": f"A21-{self.token_calls}", "expires_in": 32400}
            )
        assert request.headers["authorization"].startswith("Bearer A21-")
        if self.fail_next:
            code = self.fail_next.pop(0)
            return httpx.Response(
                code,
                headers={"paypal-debug-id": "dbg123"},
                json={
                    "name": "ERR",
                    "message": f"status {code}",
                    "details": [{"issue": f"ISSUE_{code}"}],
                },
            )
        rid = request.headers.get("paypal-request-id")
        if rid and rid in self.by_request_id:
            return httpx.Response(200, json=self.by_request_id[rid])
        if path == "/v2/checkout/orders" and request.method == "POST":
            body = json.loads(request.content)
            oid = f"5O{len(self.orders) + 1:015d}"
            unit = body["purchase_units"][0]
            order = {
                "id": oid,
                "status": "PAYER_ACTION_REQUIRED",
                "intent": "CAPTURE",
                "purchase_units": [unit],
                "links": [
                    {
                        "rel": "payer-action",
                        "href": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}",
                    }
                ],
            }
            self.orders[oid] = order
            if rid:
                self.by_request_id[rid] = order
            return httpx.Response(201, json=order)
        if path.endswith("/capture") and request.method == "POST":
            oid = path.split("/")[-2]
            order = self.orders.get(oid)
            if order is None:
                return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND", "message": "nf"})
            amount = order["purchase_units"][0]["amount"]
            body = {
                "id": oid,
                "status": "COMPLETED",
                "payer": {"payer_id": "QYR5Z8XDVJNXQ", "email_address": "buyer@example.com"},
                "purchase_units": [
                    {
                        "payments": {
                            "captures": [
                                {
                                    "id": f"CAP{oid[-8:]}",
                                    "status": self.capture_status,
                                    "amount": {
                                        "currency_code": amount["currency_code"],
                                        "value": self.capture_amount_override or amount["value"],
                                    },
                                    "create_time": "2026-10-10T12:00:00Z",
                                    "seller_protection": {"status": "ELIGIBLE"},
                                }
                            ]
                        }
                    }
                ],
            }
            if rid:
                self.by_request_id[rid] = body
            return httpx.Response(201, json=body)
        if path.startswith("/v1/customer/disputes"):
            return httpx.Response(
                403,
                json={
                    "name": "NOT_AUTHORIZED",
                    "message": "Authorization failed due to insufficient permissions",
                },
            )
        return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND", "message": path})
