import type { TransactionStatus } from "@/lib/api";
import { humanize } from "@/lib/format";

import { Badge, type Tone } from "./Badge";

const TONE: Record<TransactionStatus, Tone> = {
  ORDER_CREATED: "neutral",
  CAPTURE_PENDING: "warning",
  CAPTURED: "positive",
  CAPTURE_DECLINED: "critical",
  CAPTURE_FAILED: "critical",
  REFUNDED: "accent",
  PARTIALLY_REFUNDED: "accent",
};

export function StatusBadge({ status }: { status: TransactionStatus }) {
  return <Badge tone={TONE[status]}>{humanize(status)}</Badge>;
}
