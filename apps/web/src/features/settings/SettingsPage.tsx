import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { useMe } from "@/features/auth/session";
import { api, type AuditPage } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

import { usePayPalStatus } from "./usePayPalStatus";

export function SettingsPage() {
  const me = useMe();
  const status = usePayPalStatus();
  return (
    <>
      <PageHeader title="Settings" description="Connection status and workspace information. Live PayPal mode is intentionally not available." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="PayPal connection">
          {status.isPending && <Skeleton className="h-28" />}
          {status.isError && <ErrorState error={status.error} onRetry={() => void status.refetch()} />}
          {status.data && (
            <dl className="grid grid-cols-[minmax(0,10rem)_1fr] gap-x-4 gap-y-2.5 text-sm">
              <dt className="text-fg-subtle">Gateway</dt>
              <dd className="flex flex-wrap items-center gap-2">
                {status.data.mode === "sandbox" ? "PayPal REST (sandbox host)" : "Offline fixture"}
                <OriginBadge origin={status.data.data_origin} />
              </dd>
              <dt className="text-fg-subtle">Credentials</dt>
              <dd>{status.data.credentials_configured ? <Badge tone="positive">Configured</Badge> : <Badge tone="warning">Not configured</Badge>}</dd>
              <dt className="text-fg-subtle">OAuth2 token</dt>
              <dd>
                <Badge tone={status.data.token_check === "ok" ? "positive" : status.data.token_check === "failed" ? "critical" : "neutral"}>
                  {humanize(status.data.token_check)}
                </Badge>
                {status.data.token_error && <p className="mt-1 text-xs text-fg-muted">{status.data.token_error}</p>}
              </dd>
              <dt className="text-fg-subtle">Webhook ID</dt>
              <dd>{status.data.webhook_id_configured ? <Badge tone="positive">Configured</Badge> : <Badge tone="warning">Not configured</Badge>}</dd>
              <dt className="text-fg-subtle">Client ID</dt>
              <dd className="truncate font-mono text-xs leading-5">{status.data.client_id ?? "—"}</dd>
            </dl>
          )}
        </Panel>
        <Panel title="Your access">
          {me.data && (
            <dl className="grid grid-cols-[minmax(0,10rem)_1fr] gap-x-4 gap-y-2.5 text-sm">
              <dt className="text-fg-subtle">Merchant</dt>
              <dd>{me.data.merchant.name}</dd>
              <dt className="text-fg-subtle">Environment</dt>
              <dd>{humanize(me.data.merchant.environment)}</dd>
              <dt className="text-fg-subtle">Signed in as</dt>
              <dd className="truncate">{me.data.email}</dd>
              <dt className="text-fg-subtle">Role</dt>
              <dd><Badge tone="accent">{me.data.role}</Badge></dd>
              <dt className="text-fg-subtle">AI provider</dt>
              <dd className="text-fg-muted">Not configured (investigation agent arrives in Phase 4)</dd>
            </dl>
          )}
        </Panel>
        {me.data?.role === "ADMIN" && <AuditLog />}
      </div>
    </>
  );
}

function AuditLog() {
  const q = useQuery({ queryKey: ["audit"], queryFn: () => api<AuditPage>("/audit?limit=25") });
  return (
    <Panel title="Audit log" className="lg:col-span-2" bodyClassName="p-0">
      {q.isPending && <Skeleton className="m-4 h-40" />}
      {q.isError && <div className="p-4"><ErrorState error={q.error} /></div>}
      {q.data?.items.length === 0 && <EmptyState title="No audit events" />}
      {q.data && q.data.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-fg-subtle">
                <th className="px-4 py-2 font-medium">When</th>
                <th className="px-4 py-2 font-medium">Action</th>
                <th className="px-4 py-2 font-medium">Actor</th>
                <th className="px-4 py-2 font-medium">Entity</th>
                <th className="px-4 py-2 font-medium">Correlation</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((a) => (
                <tr key={a.id} className="border-t border-line">
                  <td className="tabular px-4 py-2 text-fg-muted">{formatDateTime(a.created_at)}</td>
                  <td className="px-4 py-2 font-mono text-xs">{a.action}</td>
                  <td className="px-4 py-2 text-fg-muted">{humanize(a.actor_type)}</td>
                  <td className="px-4 py-2 text-fg-muted">{a.entity_type}</td>
                  <td className="px-4 py-2 font-mono text-xs text-fg-subtle">{a.correlation_id?.slice(0, 12) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
