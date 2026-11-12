import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { api, type DataOrigin, type Schemas } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

type Monitoring = Schemas["MonitoringOut"];
const ORIGINS: DataOrigin[] = [
  "SYNTHETIC_DEMO",
  "SIMULATED",
  "LIVE_SANDBOX",
  "MERCHANT_PROVIDED",
];
export const percent = (value: number | null) =>
  value === null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;

export function MonitoringPage() {
  const [origin, setOrigin] = useState<DataOrigin>("SYNTHETIC_DEMO");
  const [days, setDays] = useState(90);
  const [capacity, setCapacity] = useState(8);
  const q = useQuery({
    queryKey: ["risk-monitoring", origin, days, capacity],
    queryFn: () =>
      api<Monitoring>(
        `/monitoring/risk?data_origin=${origin}&days=${days}&capacity=${capacity / 100}`,
      ),
  });
  return (
    <>
      <PageHeader
        title="Risk monitoring"
        description="Recorded merchant activity and score shifts. Drift is an investigation signal, never proof of fraud or model failure."
      />
      <div className="workspace-toolbar">
        <label className="text-sm">
          Data origin
          <select
            aria-label="Data origin"
            className="mt-1 block rounded border border-line bg-surface p-2"
            value={origin}
            onChange={(e) => setOrigin(e.target.value as DataOrigin)}
          >
            {ORIGINS.map((o) => (
              <option key={o} value={o}>
                {humanize(o)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Window
          <select
            aria-label="Monitoring window"
            className="mt-1 block rounded border border-line bg-surface p-2"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            {[7, 30, 90, 180].map((n) => (
              <option key={n} value={n}>
                {n} days vs previous {n}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Illustrative review capacity (%)
          <input
            aria-label="Review capacity percent"
            type="number"
            min={1}
            max={100}
            className="mt-1 block w-24 rounded border border-line bg-surface p-2"
            value={capacity}
            onChange={(e) =>
              setCapacity(
                Math.min(100, Math.max(1, Number(e.target.value) || 1)),
              )
            }
          />
        </label>
        <Link
          to="/app/operations"
          className="text-sm text-accent hover:underline"
        >
          Administrator operations
        </Link>
      </div>
      {q.isPending && <Skeleton className="h-64" />}
      {q.isError && (
        <ErrorState error={q.error} onRetry={() => void q.refetch()} />
      )}
      {q.data && <MonitoringBody data={q.data} />}
    </>
  );
}

function MonitoringBody({ data }: { data: Monitoring }) {
  return (
    <>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-fg-muted">
        <OriginBadge origin={data.data_origin} />
        <span>Observed {formatDateTime(data.observed_at)}</span>
      </div>
      <p className="mb-4 text-xs text-fg-muted">
        Current: {formatDateTime(data.current_window.start)} to{" "}
        {formatDateTime(data.current_window.end)}. Reference:{" "}
        {formatDateTime(data.reference_window.start)} to{" "}
        {formatDateTime(data.reference_window.end)}. End timestamps are
        exclusive.
      </p>
      {data.truncated && (
        <p role="alert" className="mb-4 text-sm text-warning">
          Results are truncated to {data.sample_limit.toLocaleString()} records.
          Narrow the window; these counts do not describe the complete
          population.
        </p>
      )}
      {data.capacity_utilization !== null && data.capacity_utilization > 1 && (
        <p
          role="alert"
          className="mb-4 rounded border border-warning/40 p-3 text-sm text-warning"
        >
          Recorded HIGH share exceeds the illustrative review capacity. Review
          staffing and policy assumptions; no threshold is changed.
        </p>
      )}
      <div className="workspace-analytics-layout">
        <Panel title="Current window">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Metric
              label="Transactions"
              value={data.current_transactions.toLocaleString()}
            />
            <Metric
              label="Scored payments"
              value={data.current_scored.toLocaleString()}
            />
            <Metric
              label="HIGH share of scored"
              value={percent(data.high_flag_rate)}
            />
            <Metric
              label="Capacity utilization"
              value={percent(data.capacity_utilization)}
            />
          </dl>
          <p className="mt-3 text-xs text-fg-muted">
            Capacity is an illustrative share of scored payments, not staffed
            hours. It changes no serving threshold.
          </p>
        </Panel>
        <Panel title="Review outcomes">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Metric
              label="Pending cases (all ages)"
              value={String(data.open_cases)}
            />
            <Metric label="Overdue" value={String(data.overdue_cases)} />
            <Metric
              label="Oldest pending"
              value={
                data.oldest_pending_hours === null
                  ? "None"
                  : `${data.oldest_pending_hours.toFixed(1)} hours`
              }
            />
            <Metric
              label="New-case resolution rate"
              value={percent(data.resolution_rate)}
            />
            <Metric
              label="Resolved during window"
              value={String(data.resolved_in_window)}
            />
            <Metric
              label="Analyst adverse resolutions"
              value={String(data.confirmed_adverse_cases)}
            />
          </dl>
          <p className="mt-3 text-xs text-fg-muted">
            The rate is the share of cases opened in the current window that
            were resolved by its end. Analyst labels can be delayed and are not
            independent fraud verification.
          </p>
        </Panel>
        <Panel title="Transaction volume over time">
          {data.transaction_volume.length === 0 ? (
            <EmptyState title="No transactions in this window" />
          ) : (
            <Bars
              rows={data.transaction_volume.map((d) => ({
                label: d.date,
                count: d.count,
              }))}
              label="Recorded transaction volume"
            />
          )}
        </Panel>
        <Panel title="Risk bands and model versions">
          {data.current_scored === 0 ? (
            <EmptyState title="No scored payments in this window" />
          ) : (
            <>
              <Bars
                rows={Object.entries(data.risk_bands).map(([label, count]) => ({
                  label,
                  count,
                }))}
                label="Risk band counts"
              />
              <ul className="mt-4 space-y-1 text-sm">
                {Object.entries(data.model_versions).map(([version, count]) => (
                  <li key={version}>
                    {version}: {count}
                  </li>
                ))}
              </ul>
            </>
          )}
        </Panel>
        <Panel title="Prediction score distribution">
          <p className="mb-3 text-xs text-fg-muted">
            Current / reference counts. Each payment contributes its latest
            assessment recorded before the selected end.
          </p>
          <ul className="space-y-1 text-sm">
            {data.score_distribution.map((bin) => (
              <li key={bin.lower} className="flex justify-between gap-4">
                <span>
                  {bin.lower.toFixed(1)}–{bin.upper.toFixed(1)}
                </span>
                <span className="tabular">
                  {bin.current_count} / {bin.reference_count}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Score shift and calibration">
          <p className="text-sm">
            Population Stability Index:{" "}
            <strong>
              {data.score_psi === null
                ? "Unavailable"
                : data.score_psi.toFixed(4)}
            </strong>
          </p>
          <p className="mt-2 text-xs text-fg-muted">{data.psi_note}</p>
          <p className="mt-3 text-sm">Calibration: {data.calibration_status}</p>
          <p className="mt-2 text-xs text-fg-muted">
            Synthetic benchmark calibration is separately available in the
            Policy Lab. It is not live merchant calibration.
          </p>
        </Panel>
        <Panel title="Case arrivals" className="lg:col-span-2">
          {data.case_growth.length === 0 ? (
            <EmptyState title="No cases opened in this window" />
          ) : (
            <Bars
              rows={data.case_growth.map((d) => ({
                label: d.date,
                count: d.count,
              }))}
              label="Cases opened per date"
            />
          )}
        </Panel>
        <Panel title="Feature missingness and means" className="lg:col-span-2">
          <p className="mb-3 text-xs text-fg-muted">
            Reference → current, based on recorded feature snapshots. A shift
            does not establish degradation. Units follow the existing serving
            features.
          </p>
          <div
            tabIndex={0}
            role="region"
            aria-label="Monitoring data table 1"
            className="overflow-x-auto"
          >
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="text-fg-subtle">
                  <th className="p-2">Feature</th>
                  <th className="p-2">Missing reference → current</th>
                  <th className="p-2">Mean reference → current</th>
                </tr>
              </thead>
              <tbody>
                {data.feature_comparison.map((f) => (
                  <tr className="border-t border-line" key={f.feature}>
                    <td className="p-2">{humanize(f.feature)}</td>
                    <td className="p-2">
                      {percent(f.reference_missing_rate)} →{" "}
                      {percent(f.current_missing_rate)}
                    </td>
                    <td className="tabular p-2">
                      {f.reference_mean?.toFixed(3) ?? "Unavailable"} →{" "}
                      {f.current_mean?.toFixed(3) ?? "Unavailable"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Interpretation limits" className="lg:col-span-2">
          <ul className="list-disc space-y-1 pl-5 text-xs text-fg-muted">
            {data.limitations.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-fg-subtle">{label}</dt>
      <dd className="tabular mt-1 text-lg">{value}</dd>
    </div>
  );
}

function Bars({
  rows,
  label,
}: {
  rows: { label: string; count: number }[];
  label: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <ul
      aria-label={label}
      tabIndex={0}
      className="monitoring-bars max-h-64 space-y-2 overflow-y-auto"
    >
      {rows.map((row) => (
        <li key={row.label} className="text-sm">
          <div className="monitoring-bar-label-row flex justify-between gap-3">
            <span>{row.label}</span>
            <span className="monitoring-bar-count tabular">{row.count}</span>
          </div>
          <div aria-hidden className="mt-1 h-1.5 rounded bg-sunken">
            <div
              className="h-full rounded bg-accent"
              style={{ width: `${(row.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
