import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api, type DashboardSummary, type DataOrigin } from "@/lib/api";
import { formatDateTime, formatMoney, humanize, shortId } from "@/lib/format";

export function DashboardPage() {
  const q = useQuery({ queryKey: ["dashboard"], queryFn: () => api<DashboardSummary>("/dashboard/summary") });

  return (
    <>
      <PageHeader
        title="Command Center"
        description="Payment activity recorded by SENTINEL. Totals are split by data origin; sandbox and simulated money are never added together."
      />
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.isPending && <DashboardSkeleton />}
      {q.data && <DashboardBody data={q.data} />}
    </>
  );
}

function DashboardBody({ data }: { data: DashboardSummary }) {
  const captured = data.by_status["CAPTURED"] ?? 0;
  const failed = (data.by_status["CAPTURE_FAILED"] ?? 0) + (data.by_status["CAPTURE_DECLINED"] ?? 0);
  const open = (data.by_status["ORDER_CREATED"] ?? 0) + (data.by_status["CAPTURE_PENDING"] ?? 0);
  const events = Object.values(data.webhook_events).reduce((a, b) => a + b, 0);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Panel title="Captured volume" className="lg:col-span-2">
        {data.captured_by_origin.length === 0 ? (
          <EmptyState title="No captured payments yet" action={<Link className="text-sm text-accent hover:underline" to="/checkout">Run a sandbox checkout</Link>}>
            Volume appears here once PayPal confirms a capture.
          </EmptyState>
        ) : (
          <ul className="divide-y divide-line">
            {data.captured_by_origin.map((row) => (
              <li key={`${row.data_origin}-${row.currency}`} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <OriginBadge origin={row.data_origin} />
                <div className="text-right">
                  <p className="tabular text-2xl font-semibold">{formatMoney(row.captured_amount_minor, row.currency)}</p>
                  <p className="tabular text-xs text-fg-subtle">
                    {row.captured_count} capture{row.captured_count === 1 ? "" : "s"} · {row.currency}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Payment states">
        <dl className="grid grid-cols-3 gap-3">
          <Stat label="Captured" value={captured} />
          <Stat label="Awaiting" value={open} />
          <Stat label="Failed" value={failed} tone={failed > 0 ? "critical" : undefined} />
        </dl>
        <p className="mt-4 border-t border-line pt-3 text-xs text-fg-subtle">
          {events === 0 ? (
            "No PayPal webhook events linked to this merchant yet."
          ) : (
            <>
              Webhook events:{" "}
              {Object.entries(data.webhook_events)
                .map(([k, v]) => `${v} ${humanize(k).toLowerCase()}`)
                .join(" · ")}
            </>
          )}
        </p>
      </Panel>
      <RiskOverview data={data} />
      <Panel
        title="Recent payments"
        className="lg:col-span-3"
        bodyClassName="p-0"
        actions={
          <Link to="/transactions" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
            All transactions <ArrowRight aria-hidden className="size-3.5" />
          </Link>
        }
      >
        {data.recent.length === 0 ? (
          <EmptyState title="No transactions" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="text-left text-xs text-fg-subtle">
                  <th className="px-4 py-2 font-medium">PayPal order</th>
                  <th className="px-4 py-2 font-medium">Item</th>
                  <th className="px-4 py-2 text-right font-medium">Amount</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Origin</th>
                  <th className="px-4 py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.recent.map((t) => (
                  <tr key={t.id} className="border-t border-line hover:bg-raised">
                    <td className="px-4 py-2.5 font-mono text-xs">
                      <Link to={`/transactions/${t.id}`} className="text-accent hover:underline">
                        {shortId(t.paypal_order_id, 12)}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-fg-muted">{t.product_name ?? "—"}</td>
                    <td className="tabular px-4 py-2.5 text-right">{formatMoney(t.amount_minor, t.currency)}</td>
                    <td className="px-4 py-2.5"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-2.5"><OriginBadge origin={t.data_origin} /></td>
                    <td className="tabular px-4 py-2.5 text-fg-muted">{formatDateTime(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}

const BANDS = ["HIGH", "MEDIUM", "LOW"] as const;
const BAND_COLOR: Record<(typeof BANDS)[number], string> = { HIGH: "bg-critical", MEDIUM: "bg-warning", LOW: "bg-positive" };

function RiskOverview({ data }: { data: DashboardSummary }) {
  const origins = [...new Set([...data.risk_bands_by_origin, ...data.open_cases_by_origin].map((r) => r.data_origin))];
  const openFor = (o: DataOrigin) => data.open_cases_by_origin.filter((r) => r.data_origin === o).reduce((a, r) => a + r.count, 0);
  return (
    <Panel
      title="Risk and review"
      className="lg:col-span-3"
      actions={
        <Link to="/cases" className="inline-flex items-center gap-1 text-sm text-accent hover:underline">
          Review queue <ArrowRight aria-hidden className="size-3.5" />
        </Link>
      }
    >
      {origins.length === 0 ? (
        <EmptyState title="No payments scored yet">Captured payments are scored automatically. Scores are model-generated decision support.</EmptyState>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {origins.map((o) => {
            const bands = Object.fromEntries(data.risk_bands_by_origin.filter((r) => r.data_origin === o).map((r) => [r.key, r.count]));
            const scored = BANDS.reduce((a, b) => a + (bands[b] ?? 0), 0);
            return (
              <li key={o} className="rounded-md border border-line p-3">
                <div className="flex items-center justify-between gap-3">
                  <OriginBadge origin={o} />
                  <p className="text-sm">
                    <span className="tabular text-xl font-semibold">{openFor(o)}</span>
                    <span className="ml-1.5 text-fg-muted">open case{openFor(o) === 1 ? "" : "s"}</span>
                  </p>
                </div>
                {scored > 0 && (
                  <>
                    <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-sunken" aria-hidden>
                      {BANDS.map((b) => (
                        <span key={b} className={BAND_COLOR[b]} style={{ width: `${((bands[b] ?? 0) / scored) * 100}%` }} />
                      ))}
                    </div>
                    <p className="tabular mt-2 text-xs text-fg-muted">
                      {scored} scored: {BANDS.map((b) => `${bands[b] ?? 0} ${b.toLowerCase()}`).join(" · ")}
                    </p>
                  </>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Panel>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "critical" }) {
  return (
    <div>
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className={`tabular mt-1 text-2xl font-semibold ${tone === "critical" ? "text-critical" : ""}`}>{value}</dd>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-3" aria-busy="true" aria-label="Loading dashboard">
      <Skeleton className="h-40 lg:col-span-2" />
      <Skeleton className="h-40" />
      <Skeleton className="h-64 lg:col-span-3" />
    </div>
  );
}
