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


class InvestigationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InvestigationMode(StrEnum):
    """How the findings were produced. Only AI_AGENT output is model-generated analysis."""

    AI_AGENT = "AI_AGENT"
    DETERMINISTIC = "DETERMINISTIC"


class InvestigationErrorCategory(StrEnum):
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    UNSUPPORTED_ASSERTION = "UNSUPPORTED_ASSERTION"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    ABANDONED = "ABANDONED"
    INTERNAL = "INTERNAL"


class EvidenceCategory(StrEnum):
    """What the merchant says a document is. Declared by the uploader, never verified."""

    INVOICE = "INVOICE"
    SHIPPING_PROOF = "SHIPPING_PROOF"
    DELIVERY_CONFIRMATION = "DELIVERY_CONFIRMATION"
    CUSTOMER_COMMUNICATION = "CUSTOMER_COMMUNICATION"
    REFUND_POLICY = "REFUND_POLICY"
    OTHER = "OTHER"


class ExtractionStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    NO_TEXT = "NO_TEXT"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    FAILED = "FAILED"


class ApprovalActionType(StrEnum):
    MANUAL_REVIEW = "MANUAL_REVIEW"
    EVIDENCE_PACKET_INTERNAL = "EVIDENCE_PACKET_INTERNAL"
    PREPARE_REFUND = "PREPARE_REFUND"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalDecisionValue(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExecutionStatus(StrEnum):
    """What happened after approval. Financial actions stay NOT_EXECUTED until Phase 5."""

    COMPLETED_INTERNAL = "COMPLETED_INTERNAL"
    NOT_EXECUTED = "NOT_EXECUTED"
