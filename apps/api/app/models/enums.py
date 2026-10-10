"""Domain states. The frontend mirrors these via packages/contracts (generated from OpenAPI)."""

from enum import StrEnum


class DataOrigin(StrEnum):
    """Where a record came from. Shown on every screen that displays it."""

    LIVE_SANDBOX = "LIVE_SANDBOX"
    MERCHANT_PROVIDED = "MERCHANT_PROVIDED"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    SIMULATED = "SIMULATED"


class Role(StrEnum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class MerchantEnvironment(StrEnum):
    SANDBOX = "SANDBOX"
    DEMO = "DEMO"


class TransactionStatus(StrEnum):
    ORDER_CREATED = "ORDER_CREATED"
    CAPTURE_PENDING = "CAPTURE_PENDING"
    CAPTURED = "CAPTURED"
    CAPTURE_DECLINED = "CAPTURE_DECLINED"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class EventVerification(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    FIXTURE = "FIXTURE"


class EventProcessing(StrEnum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
