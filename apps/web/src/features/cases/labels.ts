import type { Tone } from "@/components/ui/Badge";
import type { CasePriority, CaseResolution, CaseStatus } from "@/lib/api";

export const STATUS_LABEL: Record<CaseStatus, string> = { OPEN: "Open", IN_REVIEW: "In review", RESOLVED: "Resolved" };
export const STATUS_TONE: Record<CaseStatus, Tone> = { OPEN: "warning", IN_REVIEW: "accent", RESOLVED: "neutral" };
export const PRIORITY_TONE: Record<CasePriority, Tone> = { HIGH: "critical", MEDIUM: "warning", LOW: "neutral" };
export const RESOLUTION_LABEL: Record<CaseResolution, string> = {
  CONFIRMED_ADVERSE: "Confirmed adverse",
  LEGITIMATE: "Legitimate",
  INCONCLUSIVE: "Inconclusive",
};
export const RESOLUTION_HELP: Record<CaseResolution, string> = {
  CONFIRMED_ADVERSE: "Evidence points to fraud, abuse or a likely chargeback.",
  LEGITIMATE: "The payment looks genuine; the flag was a false positive.",
  INCONCLUSIVE: "Not enough evidence either way.",
};

export function isOverdue(dueAt: string, status: CaseStatus): boolean {
  return status !== "RESOLVED" && new Date(dueAt).getTime() < Date.now();
}
