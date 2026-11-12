import { AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";

import type { ModelCard } from "@/lib/api";

import { useModelCard } from "./useRisk";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

/**
 * Review-capacity evidence must remain visible but should not resemble a
 * site-wide alert banner. Technical explanation can be expanded as needed.
 */
export function CapacityWarning({
  card,
  compact = false,
}: {
  card?: ModelCard;
  compact?: boolean;
}) {
  const q = useModelCard();
  const m = card ?? q.data;
  const cap = m?.review_capacity;
  if (!cap?.exceeded) return null;
  return (
    <aside role="note" aria-label="Review capacity warning" className="sentinel-inline-notice">
      <AlertTriangle aria-hidden className="size-4 shrink-0 text-warning" />
      <div className="min-w-0">
        <p className="font-medium text-fg">
          Review capacity exceeded on the test window: {pct(cap.test_flag_rate)} flagged vs {pct(cap.capacity_share)} planned.
        </p>
        <details className="sentinel-notice-details">
          <summary>Why this matters</summary>
          <p className="mt-1 text-fg-muted">
            {compact
              ? "Expect more high-risk cases than the threshold was planned for. The policy stays in shadow mode; the threshold was not tuned on test data. "
              : cap.message}
            {compact && (
              <Link to="/app/model" className="text-accent underline underline-offset-2">
                Model details
              </Link>
            )}
          </p>
        </details>
      </div>
    </aside>
  );
}
