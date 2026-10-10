import type { RiskAssessment } from "@/lib/api";

const SHOWN = 6;

function formatValue(feature: string, value: number): string {
  if (feature.endsWith("_log")) return `≈ $${Math.expm1(value).toFixed(0)}`;
  if (feature === "is_new_customer" || feature === "merchant_history_insufficient") return value ? "yes" : "no";
  if (feature === "amount_vs_merchant_median") return `${value.toFixed(2)}×`;
  if (feature === "hours_since_cust_prev") return value >= 720 ? "none in 30 days" : `${value.toFixed(1)} h`;
  return String(Math.round(value * 100) / 100);
}

/**
 * Exact TreeSHAP contributions (log-odds, before calibration). Bars diverge from the centre:
 * right pushes the score up, left pushes it down. Values are listed so the bar is never the
 * only carrier of meaning.
 */
export function Contributions({ assessment }: { assessment: RiskAssessment }) {
  const items = assessment.explanation.contributions.slice(0, SHOWN);
  const max = Math.max(0.01, ...items.map((c) => Math.abs(c.contribution)));
  return (
    <div>
      <ul className="space-y-2.5" aria-label="Main factors behind this score">
        {items.map((c) => {
          const up = c.contribution > 0;
          const width = `${(Math.abs(c.contribution) / max) * 50}%`;
          return (
            <li key={c.feature} className="text-sm">
              <div className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 text-fg">{c.label}</span>
                <span className="tabular shrink-0 text-xs text-fg-muted">{formatValue(c.feature, c.value)}</span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <div aria-hidden className="relative h-1.5 flex-1 rounded-full bg-sunken">
                  <span className="absolute top-0 left-1/2 h-full w-px bg-line-strong" />
                  <span
                    className={`absolute top-0 h-full rounded-full ${up ? "left-1/2 bg-critical" : "right-1/2 bg-positive"}`}
                    style={{ width }}
                  />
                </div>
                <span className={`tabular w-24 shrink-0 text-right text-xs ${up ? "text-critical" : "text-positive"}`}>
                  {up ? "raises" : "lowers"} {Math.abs(c.contribution).toFixed(2)}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-xs text-fg-subtle">
        Contributions are exact SHAP values in the model&apos;s log-odds before calibration. They explain the model, not the
        payer&apos;s intent.
      </p>
    </div>
  );
}
