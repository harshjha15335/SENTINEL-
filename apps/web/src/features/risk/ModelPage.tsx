import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Panel } from "@/components/ui/Panel";
import { formatScore } from "@/components/ui/RiskBadge";
import { ErrorState, Skeleton } from "@/components/ui/States";
import type { ModelCard, ModelMetrics } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

import { useModelCard } from "./useRisk";

export function ModelPage() {
  const q = useModelCard();
  return (
    <>
      <PageHeader
        title="Risk model"
        description="The model behind every risk score, with the numbers from its one evaluation on held-out data. Nothing on this page is typed in by hand."
      />
      {q.isPending && <Skeleton className="h-96" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && <Card m={q.data} />}
    </>
  );
}

function modelName(key: string): string {
  const base = key.split("(")[0] ?? key;
  if (base === "xgboost") return "XGBoost";
  return humanize(base);
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const num = (v: number) => v.toFixed(3);
const usd = (v: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v);

const ROWS: { key: keyof ModelMetrics; label: string; fmt: (v: number) => string; better: "high" | "low" }[] = [
  { key: "pr_auc", label: "PR-AUC", fmt: num, better: "high" },
  { key: "roc_auc", label: "ROC-AUC", fmt: num, better: "high" },
  { key: "precision", label: "Precision at threshold", fmt: pct, better: "high" },
  { key: "recall", label: "Recall at threshold", fmt: pct, better: "high" },
  { key: "f1", label: "F1", fmt: num, better: "high" },
  { key: "false_positive_rate", label: "False positive rate", fmt: pct, better: "low" },
  { key: "flag_rate", label: "Share of payments flagged", fmt: pct, better: "low" },
  { key: "brier", label: "Brier score", fmt: num, better: "low" },
  { key: "expected_cost", label: "Expected cost (assumed costs)", fmt: usd, better: "low" },
];

function Card({ m }: { m: ModelCard }) {
  const t = m.test_metrics;
  const r = m.test_metrics_rules_baseline;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div role="note" className="rounded-md border border-warning/40 bg-warning-soft px-4 py-3 text-sm lg:col-span-3">
        <p className="font-medium text-fg">Trained and tested on synthetic data only.</p>
        <p className="mt-0.5 text-fg-muted">
          {m.training_data}. These results show the method works on that scenario; they are not evidence of performance on
          real PayPal traffic.
        </p>
      </div>

      <Panel title="Held-out test results" className="lg:col-span-2" bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-sm">
            <caption className="sr-only">Model versus rules baseline on the test split</caption>
            <thead>
              <tr className="text-left text-xs text-fg-subtle">
                <th className="px-4 py-2 font-medium">Metric</th>
                <th className="px-4 py-2 text-right font-medium">{modelName(m.chosen_model)}</th>
                <th className="px-4 py-2 text-right font-medium">Rules baseline</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const a = t[row.key];
                const b = r[row.key];
                const wins = row.better === "high" ? a > b : a < b;
                return (
                  <tr key={row.key} className="border-t border-line">
                    <th scope="row" className="px-4 py-2 text-left font-normal text-fg-muted">{row.label}</th>
                    <td className={`tabular px-4 py-2 text-right ${wins ? "font-medium text-fg" : "text-fg-muted"}`}>{row.fmt(a)}</td>
                    <td className="tabular px-4 py-2 text-right text-fg-muted">{row.fmt(b)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="border-t border-line px-4 py-3 text-xs text-fg-subtle">
          {t.rows.toLocaleString()} test payments, {t.positives} adverse ({pct(t.prevalence)}). Without any review the
          assumed cost is {usd(t.expected_cost_no_review)}. The rules baseline flags payments with two or more of four
          simple red flags. The review cap of {pct(m.cost_assumptions["review_capacity_share"] ?? 0)} was enforced on
          validation; on the later test window the same threshold flagged {pct(t.flag_rate)}, so the cap is not guaranteed
          when traffic shifts.
        </p>
      </Panel>

      <Panel title="Decision bands">
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-xs text-fg-subtle">High (opens a review case)</dt>
            <dd className="tabular mt-0.5">from {formatScore(m.thresholds["high"] ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">Medium (optional review)</dt>
            <dd className="tabular mt-0.5">from {formatScore(m.thresholds["medium"] ?? 0)}</dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">How the high threshold was chosen</dt>
            <dd className="mt-0.5 text-fg-muted">
              Lowest expected cost on the validation split, reviewing at most{" "}
              {pct(m.cost_assumptions["review_capacity_share"] ?? 0)} of payments.
            </dd>
          </div>
          <div>
            <dt className="text-xs text-fg-subtle">Cost assumptions (illustrative)</dt>
            <dd className="mt-0.5 text-fg-muted">
              {usd(m.cost_assumptions["review_cost_usd"] ?? 0)} per review, {usd(m.cost_assumptions["chargeback_fee_usd"] ?? 0)} chargeback
              fee plus the payment amount, review prevents {pct(m.cost_assumptions["review_prevents_share"] ?? 0)} of the loss.
            </dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Model selection (validation split)" bodyClassName="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-fg-subtle">
              <th className="px-4 py-2 font-medium">Candidate</th>
              <th className="px-4 py-2 text-right font-medium">PR-AUC</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(m.validation_comparison).map(([name, v]) => (
              <tr key={name} className="border-t border-line">
                <th scope="row" className="px-4 py-2 text-left font-normal">
                  {modelName(name)}
                  {name === m.chosen_model && <Badge tone="accent" className="ml-2">chosen</Badge>}
                </th>
                <td className="tabular px-4 py-2 text-right">{num(v["valid_pr_auc"] ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="border-t border-line px-4 py-3 text-xs text-fg-subtle">
          {m.calibration}. Split: {String(m.split["method"])}; training ends {formatDateTime(String(m.split["train_end"]))}.
        </p>
      </Panel>

      <Panel title="Features (past events only)">
        <ul className="space-y-1.5 text-sm text-fg-muted">
          {m.features.map((f) => (
            <li key={f["name"]}>{f["label"]}</li>
          ))}
        </ul>
      </Panel>

      <Panel title="Limitations">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-fg-muted">
          {m.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-fg-subtle">
          {m.model_version} · {m.feature_version} · trained {formatDateTime(m.trained_at)}
        </p>
      </Panel>
    </div>
  );
}
