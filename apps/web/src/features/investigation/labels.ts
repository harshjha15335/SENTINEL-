import type { Tone } from "@/components/ui/Badge";
import type {
  ApprovalActionType,
  ApprovalStatus,
  EvidenceCategory,
  InvestigationRun,
  InvestigationStatus,
  RecommendedAction,
  SourceRef,
} from "@/lib/api";

export const RUN_STATUS: Record<InvestigationStatus, { label: string; tone: Tone }> = {
  QUEUED: { label: "Queued", tone: "neutral" },
  RUNNING: { label: "Running", tone: "accent" },
  COMPLETED: { label: "Completed", tone: "positive" },
  FAILED: { label: "Failed", tone: "critical" },
};

export const ERROR_HELP: Record<NonNullable<InvestigationRun["error_category"]>, string> = {
  PROVIDER_UNAVAILABLE: "The AI provider is not available or rejected SENTINEL's credentials.",
  PROVIDER_TIMEOUT: "The AI provider did not answer in time.",
  PROVIDER_ERROR: "The AI provider returned an error.",
  INVALID_OUTPUT: "The AI output did not match the required findings format, so it was discarded.",
  UNSUPPORTED_ASSERTION:
    "The AI output cited, quoted or claimed something the case records do not support, so it was discarded.",
  BUDGET_EXCEEDED: "The investigation hit its request, tool-call or token budget.",
  ABANDONED: "The run did not finish and was abandoned.",
  INTERNAL: "SENTINEL could not complete the run.",
};

export const ACTION_LABEL: Record<RecommendedAction, string> = {
  NO_FURTHER_ACTION: "No further action",
  CONTINUE_MANUAL_REVIEW: "Continue manual review",
  REQUEST_MORE_EVIDENCE: "Request more evidence",
  PREPARE_EVIDENCE_PACKET: "Prepare an evidence packet",
  CONSIDER_REFUND: "Consider a refund",
  ESCALATE: "Escalate",
};

export const SOURCE_LABEL: Record<SourceRef["kind"], string> = {
  case: "Case",
  transaction: "Payment",
  risk_assessment: "Risk assessment",
  payment_event: "Provider event",
  case_note: "Note",
  evidence: "Evidence",
  payer_history: "Earlier payment",
};

export const CATEGORY_LABEL: Record<EvidenceCategory, string> = {
  INVOICE: "Invoice / receipt",
  SHIPPING_PROOF: "Shipping proof",
  DELIVERY_CONFIRMATION: "Delivery confirmation",
  CUSTOMER_COMMUNICATION: "Buyer communication",
  REFUND_POLICY: "Refund policy",
  OTHER: "Other",
};

export const APPROVAL_ACTION: Record<ApprovalActionType, { label: string; help: string }> = {
  MANUAL_REVIEW: {
    label: "Keep in manual review",
    help: "Raise the case to high priority and keep it in review.",
  },
  EVIDENCE_PACKET_INTERNAL: {
    label: "Approve evidence packet",
    help: "Approve one generated packet for internal use. Nothing is sent to PayPal.",
  },
  PREPARE_REFUND: {
    label: "Prepare refund",
    help: "Record an approved full-refund intent. No money moves; execution arrives in a later phase and needs an admin.",
  },
};

export const APPROVAL_STATUS: Record<ApprovalStatus, { label: string; tone: Tone }> = {
  PENDING: { label: "Pending", tone: "warning" },
  APPROVED: { label: "Approved", tone: "positive" },
  REJECTED: { label: "Rejected", tone: "neutral" },
};

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export const INPUT =
  "w-full rounded-md border border-line-strong bg-sunken px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-accent focus:outline-none";
