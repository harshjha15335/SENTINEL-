"""Offline stand-in for PayPal. Everything it returns is SIMULATED and labelled as such.

It exists so the product can be developed and demonstrated without sandbox credentials.
Ids are prefixed ``SIM-`` so they can never be confused with PayPal identifiers.
"""

import hashlib
import threading
from typing import Any

from app.models.enums import DataOrigin
from app.services.paypal.types import (
    CaptureResult,
    CreateOrderInput,
    Money,
    OrderResult,
    PayPalError,
    PayPalErrorKind,
    RefundResult,
)


def _sim_id(prefix: str, seed: str) -> str:
    return f"SIM-{prefix}-{hashlib.sha256(seed.encode()).hexdigest()[:14].upper()}"


class FixturePayPalGateway:
    data_origin = DataOrigin.SIMULATED
    name = "fixture"

    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Any]] = {}
        self._by_request: dict[str, str] = {}
        self._captures: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def check_credentials(self) -> None:
        return None

    def create_order(self, order: CreateOrderInput) -> OrderResult:
        with self._lock:
            existing = self._by_request.get(order.request_id)
            if existing:
                o = self._orders[existing]
            else:
                oid = _sim_id("ORDER", order.request_id)
                o = {"id": oid, "status": "CREATED", "total": order.total}
                self._orders[oid] = o
                self._by_request[order.request_id] = oid
        return OrderResult(
            order_id=o["id"],
            status=o["status"],
            approve_url=None,
            summary={"id": o["id"], "status": o["status"], "simulated": True},
        )

    def capture_order(self, order_id: str, *, request_id: str) -> CaptureResult:
        with self._lock:
            o = self._orders.get(order_id)
            if o is None:
                raise PayPalError(PayPalErrorKind.NOT_FOUND, "Simulated order not found")
            if o["status"] != "COMPLETED":
                cid = _sim_id("CAPTURE", order_id)
                o["status"] = "COMPLETED"
                o["capture_id"] = cid
                self._captures[cid] = {"id": cid, "status": "COMPLETED", "amount": o["total"]}
            total: Money = o["total"]
            cid = o["capture_id"]
        return CaptureResult(
            order_id=order_id,
            order_status="COMPLETED",
            capture_id=cid,
            capture_status="COMPLETED",
            amount=total,
            payer_id="SIM-PAYER",
            create_time=None,
            summary={"order_id": order_id, "capture_id": cid, "simulated": True},
        )

    def get_order(self, order_id: str) -> dict[str, Any]:
        o = self._orders.get(order_id)
        if o is None:
            raise PayPalError(PayPalErrorKind.NOT_FOUND, "Simulated order not found")
        return {"id": o["id"], "status": o["status"], "simulated": True}

    def get_capture(self, capture_id: str) -> dict[str, Any]:
        c = self._captures.get(capture_id)
        if c is None:
            raise PayPalError(PayPalErrorKind.NOT_FOUND, "Simulated capture not found")
        return {"id": c["id"], "status": c["status"], "simulated": True}

    def refund_capture(
        self, capture_id: str, *, amount: Money | None, request_id: str, note: str | None
    ) -> RefundResult:
        c = self._captures.get(capture_id)
        if c is None:
            raise PayPalError(PayPalErrorKind.NOT_FOUND, "Simulated capture not found")
        rid = _sim_id("REFUND", request_id)
        return RefundResult(rid, "COMPLETED", amount or c["amount"], {"id": rid, "simulated": True})

    def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        raise PayPalError(
            PayPalErrorKind.NOT_CONFIGURED, "Disputes are not available in fixture mode"
        )

    def list_disputes(self, *, page_size: int = 20) -> dict[str, Any]:
        raise PayPalError(
            PayPalErrorKind.NOT_CONFIGURED, "Disputes are not available in fixture mode"
        )
