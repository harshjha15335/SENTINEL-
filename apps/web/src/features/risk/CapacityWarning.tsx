import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";

import type { ModelCard } from "@/lib/api";

import { useModelCard } from "./useRisk";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/** Review-capacity warning from the model's recorded metadata. Renders nothing when within capacity. */
export function CapacityWarning({ card, compact = false }: { card?: ModelCard; compact?: boolean }) {
  const q = useModelCard();
  const m = card ?? q.data;
  const cap = m?.review_capacity;
  if (!cap?.exceeded) return null;
  return (
    <div role="note" aria-label="Review capacity warning" className="flex items-start gap-3 rounded-md border border-warning/40 bg-warning-soft px-4 py-3 text-sm">
      <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
      <div>
        <p className="font-medium text-fg">
          Review capacity exceeded on the test window: {pct(cap.test_flag_rate)} flagged vs {pct(cap.capacity_share)} planned.
        </p>
        <p className="mt-0.5 text-fg-muted">
          {compact
            ? "Expect more high-risk cases than the threshold was planned for. The policy stays in shadow mode; the threshold was not tuned on test data. "
            : cap.message}
          {compact && (
            <Link to="/model" className="text-accent underline underline-offset-2">
              Model details
            </Link>
          )}
        </p>
      </div>
    </div>
  );
}
