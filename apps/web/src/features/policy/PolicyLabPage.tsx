import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useMe } from "@/features/auth/session";
import { api, isOperator } from "@/lib/api";

export type PolicyParams = {
  high_threshold: number; review_capacity_share: number; false_positive_cost_usd: number;
  false_negative_cost_usd: number; investigation_cost_usd: number;
  average_value_at_risk_usd: number; recovery_share: number;
};
type Metrics = { rows: number; positives: number; tp: number; fp: number; tn: number; fn: number;
  flagged: number; precision: number; recall: number; flag_rate: number; review_capacity_count: number;
  capacity_utilization: number; over_capacity: boolean; review_cost_usd: number;
  false_positive_cost_usd: number; missed_outcome_cost_usd: number; residual_loss_usd: number;
  estimated_recoverable_usd: number; total_assumed_cost_usd: number };
type Point = { x: number; y: number };
type View = { model_version: string; validation_rows: number; validation_start: string; validation_end: string;
  frozen_test_rows: number; dataset_sha256: string; baseline_parameters: PolicyParams;
  proposed_parameters: PolicyParams; baseline: Metrics; proposed: Metrics; roc_auc: number;
  average_precision: number; brier: number; roc_curve: Point[]; precision_recall_curve: Point[];
  calibration: { mean_score: number; adverse_rate: number; count: number }[];
  thresholds: { threshold: number; flagged: number; precision: number; recall: number; total_assumed_cost_usd: number }[];
  limitations: string[] };
type Draft = { id: string; name: string; rationale: string; status: string; parameters: PolicyParams;
  requested_by_user_id: string; snapshot_sha256: string; shadow_only: boolean };

const defaults: PolicyParams = { high_threshold: 0.1036, review_capacity_share: 0.08,
  false_positive_cost_usd: 0, false_negative_cost_usd: 20, investigation_cost_usd: 4,
  average_value_at_risk_usd: 100, recovery_share: 0.7 };
const fields: { key: keyof PolicyParams; label: string; max: number; step: number }[] = [
  { key: "high_threshold", label: "HIGH threshold", max: 1, step: 0.001 },
  { key: "review_capacity_share", label: "Review capacity (share)", max: 1, step: 0.01 },
  { key: "false_positive_cost_usd", label: "False-positive cost (USD)", max: 1000000, step: 1 },
  { key: "false_negative_cost_usd", label: "Missed-outcome fee (USD)", max: 1000000, step: 1 },
  { key: "investigation_cost_usd", label: "Investigation cost per flag (USD)", max: 1000000, step: 1 },
  { key: "average_value_at_risk_usd", label: "Average value at risk (USD)", max: 1000000, step: 1 },
  { key: "recovery_share", label: "Assumed recoverable share", max: 1, step: 0.01 },
];
const pct = (n: number) => `${(100 * n).toFixed(1)}%`;
const usd = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);

export function PolicyLabPage() {
  const [params, setParams] = useState<PolicyParams>(defaults);
  const me = useMe();
  const query = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]));
  const q = useQuery({ queryKey: ["policy-simulation", query.toString()], queryFn: () => api<View>(`/policy-lab/simulate?${query}`) });
  const [valid, setValid] = useState(true);
  return <>
    <PageHeader title="Policy Lab" description="Validation-only decision simulation. Proposals remain shadow policies; approval never activates a serving threshold." />
    <div role="note" className="mb-4 rounded-md border border-warning/40 bg-warning-soft p-4 text-sm">
      <OriginBadge origin="SYNTHETIC_DEMO" /><p className="mt-2">Experiments use the frozen scenario’s validation split, never its held-out test payments. Costs and recoverable amounts are assumptions, not actual merchant losses or money recovered.</p>
    </div>
    <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
      <Panel title="Proposed policy">
        <div className="space-y-3">{fields.map(f => <label key={f.key} className="block text-sm">{f.label}
          <input className="mt-1 block w-full rounded-md border border-line bg-surface px-3 py-2" type="number" min={f.key === "review_capacity_share" ? 0.001 : 0} max={f.max} step={f.step} value={params[f.key]}
            onChange={e => { const n = Number(e.target.value); const ok = Number.isFinite(n) && n >= (f.key === "review_capacity_share" ? 0.001 : 0) && n <= f.max; setValid(ok); if (ok) setParams(p => ({ ...p, [f.key]: n })); }} />
        </label>)}</div>
        {!valid && <p role="alert" className="mt-2 text-sm text-critical">Use a value within the displayed bounds.</p>}
        <Button className="mt-4" variant="secondary" onClick={() => { setParams(defaults); setValid(true); }}>Reset assumptions</Button>
      </Panel>
      <div className="min-w-0 space-y-4">
        {q.isPending && <Skeleton className="h-64" />}
        {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
        {q.data && <>
          <Panel title="Baseline versus proposed">
            <p className="mb-3 text-xs text-fg-muted">{q.data.model_version} · {q.data.validation_rows.toLocaleString()} validation payments · {q.data.frozen_test_rows.toLocaleString()} test payments excluded. Dataset {q.data.dataset_sha256.slice(0, 12)}…</p>
            <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="py-2">Measure</th><th>Frozen threshold</th><th>Proposed</th></tr></thead><tbody>
              {[
                ["Threshold", String(q.data.baseline_parameters.high_threshold), String(params.high_threshold)],
                ["Flagged", q.data.baseline.flagged, q.data.proposed.flagged],
                ["Precision", pct(q.data.baseline.precision), pct(q.data.proposed.precision)],
                ["Recall", pct(q.data.baseline.recall), pct(q.data.proposed.recall)],
                ["Flag share", pct(q.data.baseline.flag_rate), pct(q.data.proposed.flag_rate)],
                ["Assumed total cost", usd(q.data.baseline.total_assumed_cost_usd), usd(q.data.proposed.total_assumed_cost_usd)],
              ].map(([label, a, b]) => <tr key={label} className="border-t border-line"><th className="py-2 font-normal">{label}</th><td>{a}</td><td>{b}</td></tr>)}
            </tbody></table></div>
            <p className="mt-3 text-xs text-fg-muted">Both columns use the same displayed cost/capacity assumptions; only the threshold differs. The original published test benchmark is unchanged.</p>
          </Panel>
          <div className="grid gap-4 md:grid-cols-2">
            <Panel title="Confusion matrix · proposed">
              <table className="w-full text-sm"><thead><tr><th>Predicted</th><th>Adverse</th><th>Not adverse</th></tr></thead><tbody>
                <tr><th className="py-3">Flagged</th><td className="text-center">TP {q.data.proposed.tp}</td><td className="text-center">FP {q.data.proposed.fp}</td></tr>
                <tr><th className="py-3">Not flagged</th><td className="text-center">FN {q.data.proposed.fn}</td><td className="text-center">TN {q.data.proposed.tn}</td></tr>
              </tbody></table>
            </Panel>
            <Panel title="Review capacity">
              <Badge tone={q.data.proposed.over_capacity ? "warning" : "neutral"}>{q.data.proposed.over_capacity ? "Over capacity" : "Within assumption"}</Badge>
              <p className="mt-3 text-sm">{q.data.proposed.flagged} flags / {q.data.proposed.review_capacity_count} reviews · {pct(q.data.proposed.capacity_utilization)} utilization</p>
              <p className="mt-2 text-xs text-fg-muted">No flags are silently dropped. Costs assume all flagged rows are reviewed, even when capacity is exceeded.</p>
            </Panel>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Chart title={`ROC · AUC ${q.data.roc_auc.toFixed(3)}`} points={q.data.roc_curve} xLabel="False-positive rate" yLabel="Recall" />
            <Chart title={`Precision–recall · AP ${q.data.average_precision.toFixed(3)}`} points={q.data.precision_recall_curve} xLabel="Recall" yLabel="Precision" />
            <Chart title={`Calibration · Brier ${q.data.brier.toFixed(4)}`} points={q.data.calibration.map(p => ({ x: p.mean_score, y: p.adverse_rate }))} xLabel="Mean score" yLabel="Observed adverse share" />
            <Chart title="Threshold versus flag share" points={q.data.thresholds.map(p => ({ x: p.threshold, y: p.flagged / q.data.validation_rows }))} xLabel="Threshold" yLabel="Flagged share" />
            <Chart title="Threshold precision / recall" points={q.data.thresholds.map(p => ({ x: p.threshold, y: p.precision }))} secondary={q.data.thresholds.map(p => ({ x: p.threshold, y: p.recall }))} xLabel="Threshold" yLabel="Precision / recall" />
            <Panel title="Illustrative financial impact"><dl className="space-y-2 text-sm">
              {[["Reviews", q.data.proposed.review_cost_usd], ["False positives", q.data.proposed.false_positive_cost_usd], ["Missed-outcome fees", q.data.proposed.missed_outcome_cost_usd], ["Residual assumed loss", q.data.proposed.residual_loss_usd], ["Estimated recoverable value", q.data.proposed.estimated_recoverable_usd]].map(([k, v]) => <div key={k} className="flex justify-between gap-2"><dt>{k}</dt><dd>{usd(Number(v))}</dd></div>)}
            </dl><p className="mt-3 text-xs text-fg-muted">Missed adverse outcomes: {q.data.proposed.fn}. Recoverable value is not evidence that funds were recovered.</p></Panel>
          </div>
          <Panel title="Evaluation boundaries"><ul className="list-disc space-y-2 pl-5 text-xs text-fg-muted">{q.data.limitations.map(s => <li key={s}>{s}</li>)}</ul></Panel>
        </>}
      </div>
    </div>
    <Governance params={params} canWrite={isOperator(me.data?.role)} userId={me.data?.id} admin={me.data?.role === "ADMIN"} />
  </>;
}

function Chart({ title, points, secondary, xLabel, yLabel }: { title: string; points: Point[]; secondary?: Point[]; xLabel: string; yLabel: string }) {
  const path = (rows: Point[]) => rows.map((p, i) => `${i ? "L" : "M"}${40 + p.x * 270},${165 - p.y * 135}`).join(" ");
  return <Panel title={title}>
    <svg viewBox="0 0 340 205" role="img" aria-label={`${title}. Horizontal axis: ${xLabel}. Vertical axis: ${yLabel}.`} className="w-full">
      <path d="M40 30 V165 H310" fill="none" stroke="currentColor" opacity="0.4" />
      <path d={path(points)} fill="none" stroke="#37b6bd" strokeWidth="2" />
      {secondary && <path d={path(secondary)} fill="none" stroke="#e9a44a" strokeWidth="2" />}
      <text x="35" y="180" fill="currentColor" fontSize="10">0</text><text x="300" y="180" fill="currentColor" fontSize="10">1</text>
      <text x="22" y="35" fill="currentColor" fontSize="10">1</text><text x="175" y="198" textAnchor="middle" fill="currentColor" fontSize="11">{xLabel}</text>
    </svg>
    {secondary && <p className="text-xs text-fg-muted">Teal: precision · amber: recall</p>}
    <p className="text-xs text-fg-muted">{yLabel}; synthetic validation observations only.</p>
  </Panel>;
}

function Governance({ params, canWrite, userId, admin }: { params: PolicyParams; canWrite: boolean; userId: string | undefined; admin: boolean }) {
  const qc = useQueryClient();
  const [name, setName] = useState(""); const [rationale, setRationale] = useState("");
  const q = useQuery({ queryKey: ["policy-drafts"], queryFn: () => api<Draft[]>("/policy-lab/drafts") });
  const change = useMutation({ mutationFn: ({ path, body }: { path: string; body?: unknown }) => api<Draft>(path, { method: "POST", body }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["policy-drafts"] }); } });
  return <div className="mt-4"><Panel title="Shadow policy proposals">
    <p className="mb-3 text-sm text-fg-muted">Approval records independent review of the immutable snapshot. It never changes the serving threshold. No activation endpoint exists.</p>
    {canWrite && <form onSubmit={e => { e.preventDefault(); change.mutate({ path: "/policy-lab/drafts", body: { name, rationale, parameters: params } }); }} className="mb-4 grid gap-3 md:grid-cols-2">
      <label className="text-sm">Policy name<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} className="mt-1 block w-full rounded-md border border-line bg-surface p-2" /></label>
      <label className="text-sm">Rationale<textarea required minLength={10} maxLength={4000} value={rationale} onChange={e => setRationale(e.target.value)} className="mt-1 block w-full rounded-md border border-line bg-surface p-2" /></label>
      <Button disabled={change.isPending} type="submit">Save proposed snapshot</Button>
    </form>}
    {change.isError && <ErrorState error={change.error} />}
    {q.isPending && <Skeleton className="h-20" />}{q.isError && <ErrorState error={q.error} />}
    {q.data?.length === 0 && <p className="text-sm text-fg-muted">No saved policy proposals.</p>}
    <ul className="space-y-3">{q.data?.map(d => <li key={d.id} className="rounded-md border border-line p-3">
      <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">{d.name}</span><Badge>{d.status}</Badge><Badge>Shadow only</Badge></div>
      <p className="mt-2 text-sm">{d.rationale}</p><p className="mt-1 font-mono text-xs text-fg-muted">Threshold {d.parameters.high_threshold} · {d.snapshot_sha256.slice(0, 16)}…</p>
      {canWrite && d.status === "DRAFT" && d.requested_by_user_id === userId && <Button className="mt-2" disabled={change.isPending} onClick={() => change.mutate({ path: `/policy-lab/drafts/${d.id}/submit` })}>Submit for independent review</Button>}
      {admin && d.status === "PENDING_APPROVAL" && d.requested_by_user_id !== userId && <div className="mt-2 flex gap-2">{["APPROVED", "REJECTED"].map(decision => <Button key={decision} disabled={change.isPending} variant="secondary" onClick={() => change.mutate({ path: `/policy-lab/drafts/${d.id}/decide`, body: { decision } })}>{decision === "APPROVED" ? "Approve shadow proposal" : "Reject"}</Button>)}</div>}
    </li>)}</ul>
  </Panel></div>;
}
