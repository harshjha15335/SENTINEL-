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


class RiskBand(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PolicyDecision(StrEnum):
    """What the policy would do. Recorded in shadow mode: SENTINEL never blocks a payment."""

    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"


class CaseResolution(StrEnum):
    CONFIRMED_ADVERSE = "CONFIRMED_ADVERSE"
    LEGITIMATE = "LEGITIMATE"
    INCONCLUSIVE = "INCONCLUSIVE"


class CasePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CaseSource(StrEnum):
    RISK_MODEL = "RISK_MODEL"
    MANUAL = "MANUAL"
