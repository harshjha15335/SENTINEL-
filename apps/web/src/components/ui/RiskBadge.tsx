import type { RiskBand } from "@/lib/api";

import { Badge, type Tone } from "./Badge";

const TONE: Record<RiskBand, Tone> = { LOW: "positive", MEDIUM: "warning", HIGH: "critical" };

export function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

/** Band plus calibrated score. The score is a model output, never a PayPal risk signal. */
export function RiskBadge({ band, score }: { band: RiskBand; score?: number | null }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Badge tone={TONE[band]}>{band.toLowerCase()} risk</Badge>
      {score != null && <span className="tabular text-xs text-fg-muted">{formatScore(score)}</span>}
    </span>
  );
}
