import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useMe } from "@/features/auth/session";
import { api, type Schemas } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

type Operations = Schemas["OperationsOut"];
type Stage = Schemas["StageCount"];

export function OperationsPage() {
  const me = useMe();
  const allowed = me.data?.role === "ADMIN";
  const q = useQuery({
    queryKey: ["operations"],
    queryFn: () => api<Operations>("/operations/webhooks"),
    enabled: allowed,
    refetchInterval: allowed ? 15_000 : false,
  });
  if (!allowed) return <p role="alert">Administrator access required.</p>;
  return (
    <>
      <PageHeader
        title="Operations"
        description="Separate delivery, reconciliation and scoring stages. Durable acceptance does not mean a case is resolved or money was recovered."
      />
      {q.isPending && <Skeleton className="h-64" />}
      {q.isError && (
        <ErrorState error={q.error} onRetry={() => void q.refetch()} />
      )}
      {q.data && (
        <>
          <p className="mb-4 text-sm text-fg-muted">
            Observed {formatDateTime(q.data.observed_at)} · Refreshes every 15
            seconds
          </p>
          <div className="workspace-analytics-layout">
            <Panel title="Application readiness">
              <Badge tone={q.data.ready ? "positive" : "critical"}>
                {q.data.ready ? "Ready" : "Not ready"}
              </Badge>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                {Object.entries(q.data.checks).map(([key, value]) => (
                  <div key={key} className="min-w-0">
                    <dt className="text-fg-subtle">{humanize(key)}</dt>
                    <dd className="break-words">{humanize(value)}</dd>
                  </div>
                ))}
              </dl>
            </Panel>
            <Panel title="Worker heartbeats">
              {q.data.workers.length === 0 && (
                <p className="text-sm text-fg-muted">
                  No worker heartbeat recorded.
                </p>
              )}
              <ul className="space-y-4">
                {q.data.workers.map((w) => (
                  <li key={w.name} className="text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <span>{humanize(w.name)}</span>
                      <Badge
                        tone={
                          w.fresh && w.status === "HEALTHY"
                            ? "positive"
                            : "critical"
                        }
                      >
                        {w.fresh ? humanize(w.status) : "Stale"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-fg-muted">
                      Heartbeat: {formatDateTime(w.heartbeat_at)} · Tasks:{" "}
                      {w.processed} · Failures: {w.failures}
                    </p>
                    <p className="mt-1 text-xs text-fg-muted">
                      Last accepted task:{" "}
                      {w.last_success_at
                        ? formatDateTime(w.last_success_at)
                        : "None recorded"}
                      {w.last_error ? ` · ${w.last_error}` : ""}
                    </p>
                    {w.name.includes("bridge") && (
                      <p className="mt-1 text-xs text-fg-muted">
                        Last successful poll:{" "}
                        {w.last_successful_poll_at
                          ? formatDateTime(w.last_successful_poll_at)
                          : "None recorded"}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title="Supabase inbox">
              {q.data.inbox_scope !== "installation_aggregate" ? (
                <p className="text-sm text-fg-muted">
                  Global inbox totals are restricted to the configured
                  installation operator. Your merchant queues appear below.
                </p>
              ) : (
                <>
                  <Badge tone={q.data.inbox_fresh ? "neutral" : "warning"}>
                    {q.data.inbox_fresh
                      ? "Recent snapshot"
                      : "Snapshot unavailable or stale"}
                  </Badge>
                  <p className="mt-2 text-xs text-fg-muted">
                    Installation aggregates across merchants. No payloads or
                    provider identifiers are shown.
                  </p>
                  {q.data.inbox && (
                    <>
                      <p className="mt-2 text-xs text-fg-muted">
                        Observed {formatDateTime(q.data.inbox.observed_at)}
                      </p>
                      {q.data.inbox.groups.length === 0 && (
                        <p className="mt-2 text-sm">
                          No inbox receipts recorded.
                        </p>
                      )}
                      <ul className="mt-3 space-y-3">
                        {q.data.inbox.groups.map((g) => (
                          <li
                            key={`${g.data_origin}-${g.status}`}
                            className="text-sm"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              <OriginBadge origin={g.data_origin} />
                              <span>
                                {humanize(g.status)}: {g.count}
                              </span>
                            </div>
                            {(g.status === "PENDING" ||
                              g.status === "RUNNING") && (
                              <p className="mt-1 text-xs text-fg-muted">
                                Oldest waiting receipt:{" "}
                                {g.oldest_received_at
                                  ? formatDateTime(g.oldest_received_at)
                                  : "Unknown"}
                              </p>
                            )}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              )}
            </Panel>
            <Panel title="External integrations">
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-fg-subtle">PayPal gateway</dt>
                  <dd>
                    {humanize(q.data.integrations.paypal_mode)} ·{" "}
                    {q.data.integrations.paypal_credentials_configured
                      ? "Credentials configured"
                      : "Credentials missing"}
                  </dd>
                </div>
                <div>
                  <dt className="text-fg-subtle">
                    Last verified merchant webhook
                  </dt>
                  <dd>
                    {q.data.integrations.last_verified_event_at
                      ? formatDateTime(
                          q.data.integrations.last_verified_event_at,
                        )
                      : "No verified merchant event recorded"}
                  </dd>
                </div>
                <div>
                  <dt className="text-fg-subtle">AI provider</dt>
                  <dd>
                    {humanize(q.data.integrations.ai_provider)} ·{" "}
                    {q.data.integrations.ai_configured
                      ? "Configured"
                      : "Deterministic fallback"}
                  </dd>
                </div>
                <div>
                  <dt className="text-fg-subtle">Last completed AI run</dt>
                  <dd>
                    {q.data.integrations.last_completed_ai_run_at
                      ? formatDateTime(
                          q.data.integrations.last_completed_ai_run_at,
                        )
                      : "No completed provider run recorded"}
                  </dd>
                </div>
              </dl>
              <p className="mt-3 text-xs text-fg-muted">
                {q.data.integrations.verification_note}
              </p>
            </Panel>
            <StagePanel
              title="Merchant event reconciliation"
              rows={q.data.events}
            />
            <StagePanel
              title="Merchant scoring queue"
              rows={q.data.scoring_jobs}
            />
            <StagePanel
              title="Merchant investigations"
              rows={q.data.investigations}
            />
            <Panel title="Private evidence storage">
              <p className="text-sm">
                Backend: {humanize(q.data.storage.backend)} · Database query:{" "}
                {q.data.storage.database_query}
              </p>
              <p className="mt-2 text-sm">
                Merchant database files: {q.data.storage.stored_files} · Bytes:{" "}
                {q.data.storage.stored_bytes.toLocaleString()}
              </p>
              <p className="mt-2 text-xs text-fg-muted">
                {q.data.storage.durability}
              </p>
              <p className="mt-2 text-sm">
                Exhausted merchant events: {q.data.exhausted_events}
              </p>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}

function StagePanel({ title, rows }: { title: string; rows: Stage[] }) {
  return (
    <Panel title={title}>
      {rows.length === 0 ? (
        <p className="text-sm text-fg-muted">No records in this stage.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((row) => (
            <li
              key={`${row.data_origin}-${row.status}`}
              className="flex flex-wrap items-center gap-2 text-sm"
            >
              <OriginBadge origin={row.data_origin} />
              <span>
                {humanize(row.status)}: {row.count}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
