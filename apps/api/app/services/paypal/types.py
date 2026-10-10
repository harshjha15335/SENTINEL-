"""Provider-neutral types for the PayPal gateway boundary."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PayPalErrorKind(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    VALIDATION = "VALIDATION"
    UNPROCESSABLE = "UNPROCESSABLE"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    NETWORK = "NETWORK"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class PayPalError(Exception):
    """A classified failure talking to PayPal. Never carries tokens or secrets."""

    def __init__(
        self,
        kind: PayPalErrorKind,
        message: str,
        *,
        status_code: int | None = None,
        debug_id: str | None = None,
        issue: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status_code = status_code
        self.debug_id = debug_id
        self.issue = issue

    @property
    def retryable(self) -> bool:
        return self.kind in {
            PayPalErrorKind.RATE_LIMITED,
            PayPalErrorKind.PROVIDER_ERROR,
            PayPalErrorKind.NETWORK,
        }


@dataclass(frozen=True)
class Money:
    """Amount in minor units (e.g. cents) plus ISO-4217 currency."""

    amount_minor: int
    currency: str

    # Zero-decimal currencies per PayPal's currency code reference.
    _ZERO_DECIMAL = frozenset({"HUF", "JPY", "TWD"})

    def to_paypal_value(self) -> str:
        if self.currency in self._ZERO_DECIMAL:
            return str(self.amount_minor)
        whole, frac = divmod(self.amount_minor, 100)
        return f"{whole}.{frac:02d}"

    @classmethod
    def from_paypal(cls, value: str, currency: str) -> "Money":
        if currency in cls._ZERO_DECIMAL:
            return cls(int(value), currency)
        whole, _, frac = value.partition(".")
        frac = (frac + "00")[:2]
        sign = -1 if whole.startswith("-") else 1
        return cls(sign * (abs(int(whole)) * 100 + int(frac)), currency)


@dataclass(frozen=True)
class LineItem:
    name: str
    sku: str
    quantity: int
    unit_amount: Money


@dataclass(frozen=True)
class CreateOrderInput:
    reference_id: str
    items: list[LineItem]
    request_id: str
    description: str | None = None

    @property
    def total(self) -> Money:
        currency = self.items[0].unit_amount.currency
        return Money(sum(i.unit_amount.amount_minor * i.quantity for i in self.items), currency)


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: str
    approve_url: str | None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaptureResult:
    order_id: str
    order_status: str
    capture_id: str | None
    capture_status: str | None
    amount: Money | None
    payer_id: str | None
    create_time: str | None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RefundResult:
    refund_id: str
    status: str
    amount: Money | None
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookHeaders:
    transmission_id: str
    transmission_time: str
    cert_url: str
    auth_algo: str
    transmission_sig: str
