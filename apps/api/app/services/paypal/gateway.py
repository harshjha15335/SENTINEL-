"""The PayPal gateway boundary. Business code depends on this protocol, not on HTTP."""

from typing import Any, Protocol

from app.models.enums import DataOrigin
from app.services.paypal.types import (
    CaptureResult,
    CreateOrderInput,
    Money,
    OrderResult,
    RefundResult,
)


class PayPalGateway(Protocol):
    #: Provenance stamped on every record this gateway's responses create.
    data_origin: DataOrigin
    #: Short name shown in the UI and logs ("sandbox" or "fixture").
    name: str

    def check_credentials(self) -> None:
        """Acquire (or reuse) an access token. Raises PayPalError on failure."""

    def create_order(self, order: CreateOrderInput) -> OrderResult: ...

    def capture_order(self, order_id: str, *, request_id: str) -> CaptureResult: ...

    def get_order(self, order_id: str) -> dict[str, Any]: ...

    def get_capture(self, capture_id: str) -> dict[str, Any]: ...

    def refund_capture(
        self, capture_id: str, *, amount: Money | None, request_id: str, note: str | None
    ) -> RefundResult: ...

    def get_dispute(self, dispute_id: str) -> dict[str, Any]: ...

    def list_disputes(self, *, page_size: int = 20) -> dict[str, Any]: ...
