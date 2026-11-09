import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { useMe } from "@/features/auth/session";
import { api, downloadUrl, isOperator, type Schemas } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

type Dispute = Schemas["DisputeOut"];
type Detail = Schemas["DisputeDetailOut"];

export function DisputesPage() {
  const me = useMe();
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [params] = useSearchParams();
  const [caseId, setCaseId] = useState(params.get("case") ?? "");
  const [page, setPage] = useState(0);
  const list = useQuery({ queryKey: ["disputes", page], queryFn: () => api<Dispute[]>(`/disputes?limit=25&offset=${page * 25}`) });
  const demo = useMutation({ mutationFn: () => api<Dispute>("/disputes/demo", { method: "POST", body: { case_id: caseId, reason: "ITEM_NOT_RECEIVED" } }), onSuccess: d => { setSelected(d.id); void qc.invalidateQueries({ queryKey: ["disputes"] }); } });
  const sync = useMutation({ mutationFn: () => api<Schemas["DisputeSyncOut"]>("/disputes/sync", { method: "POST" }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["disputes"] }); } });
  return <>
    <PageHeader title="Dispute Copilot" description="Prepare a grounded response, identify missing evidence and export for human review. External submission is disabled." />
    <div className="mb-4 flex flex-wrap items-center gap-3"><Badge tone="warning">Preparation only</Badge>{me.data?.role === "ADMIN" && <Button variant="secondary" busy={sync.isPending} onClick={() => sync.mutate()}>Read-only sandbox sync</Button>}</div>
    {sync.error && <ErrorState error={sync.error} />}
    {sync.data && <p className="mb-3 text-sm">Matched and synchronized: {sync.data.synchronized}. {sync.data.scope}</p>}
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <div className="space-y-4">
        <Panel title="Disputes">
          {list.isPending && <Skeleton className="h-40" />}
          {list.error && <ErrorState error={list.error} onRetry={() => void list.refetch()} />}
          {list.data?.length === 0 && <EmptyState title="No disputes in this workspace">A sandbox sync imports only disputes matched to this merchant’s stored captures. Offline demonstrations must be explicitly created.</EmptyState>}
          <ul className="space-y-3">{list.data?.map(d => <li key={d.id}><button onClick={() => setSelected(d.id)} className="w-full rounded border border-line p-3 text-left text-sm hover:bg-raised"><span className="block">{d.provider_dispute_id ?? "Demonstration dispute"}</span><span className="mt-1 block text-xs text-fg-muted">{humanize(d.reason)} · {humanize(d.status)}</span><span className="mt-2 block"><OriginBadge origin={d.data_origin} /></span></button></li>)}</ul>
          <div className="mt-3 flex gap-2"><Button variant="ghost" disabled={page === 0} onClick={() => setPage(p => p - 1)}>Previous</Button><Button variant="ghost" disabled={!list.data || list.data.length < 25} onClick={() => setPage(p => p + 1)}>Next</Button></div>
        </Panel>
        {isOperator(me.data?.role) && <Panel title="Explicit demonstration">
          <p className="mb-3 text-xs text-fg-muted">Requires an existing SIMULATED or SYNTHETIC_DEMO case. This never creates a PayPal dispute.</p>
          <form onSubmit={e => { e.preventDefault(); demo.mutate(); }} className="space-y-3">
            <label className="block text-sm" htmlFor="demo-dispute-case">Demo case ID</label>
            <input id="demo-dispute-case" value={caseId} onChange={e => setCaseId(e.target.value)} required className="w-full rounded border border-line bg-raised p-2 text-sm" />
            <Button busy={demo.isPending}>Create labelled demo dispute</Button>
          </form>{demo.error && <ErrorState error={demo.error} />}
        </Panel>}
      </div>
      {selected ? <DisputeDetail identity={selected} canWrite={isOperator(me.data?.role)} /> : <Panel title="Response workspace"><p className="text-sm text-fg-muted">Select a dispute to inspect its stage, evidence checklist and response drafts.</p></Panel>}
    </div>
  </>;
}

function DisputeDetail({ identity, canWrite }: { identity: string; canWrite: boolean }) {
  const me = useMe();
  const qc = useQueryClient();
  const detail = useQuery({ queryKey: ["dispute", identity], queryFn: () => api<Detail>(`/disputes/${identity}`) });
  const draft = useMutation({ mutationFn: () => api(`/disputes/${identity}/drafts`, { method: "POST" }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["dispute", identity] }); } });
  const assign = useMutation({ mutationFn: () => api(`/disputes/${identity}/assign`, { method: "POST", body: { user_id: me.data?.id } }), onSuccess: () => { void qc.invalidateQueries({ queryKey: ["dispute", identity] }); } });
  return <div className="space-y-4">
    {detail.isPending && <Skeleton className="h-64" />}
    {detail.error && <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />}
    {detail.data && <>
      <Panel title="Dispute context">
        <OriginBadge origin={detail.data.dispute.data_origin} />
        <dl className="mt-3 grid grid-cols-2 gap-2 text-sm"><dt className="text-fg-subtle">Reason</dt><dd>{humanize(detail.data.dispute.reason)}</dd><dt className="text-fg-subtle">Stage</dt><dd>{humanize(detail.data.dispute.stage)}</dd><dt className="text-fg-subtle">Status</dt><dd>{humanize(detail.data.dispute.status)}</dd><dt className="text-fg-subtle">Assigned analyst</dt><dd className="break-all">{detail.data.dispute.assigned_user_id ?? "Unassigned"}</dd><dt className="text-fg-subtle">Response deadline</dt><dd>{detail.data.dispute.response_due_at ? formatDateTime(detail.data.dispute.response_due_at) : "Not provided"}</dd></dl>
        {canWrite && <Button className="mt-3" variant="secondary" busy={assign.isPending} onClick={() => assign.mutate()}>Assign to me</Button>}
        {assign.error && <ErrorState error={assign.error} />}
        <p className="mt-3 text-sm"><Link className="text-accent hover:underline" to={`/cases/${detail.data.dispute.case_id}`}>Open evidence, case packet and independent approval</Link></p>
      </Panel>
      <Panel title="Evidence checklist"><ul className="space-y-2 text-sm">{detail.data.checklist.map(row => <li key={row.key}><Badge tone={row.provided ? "neutral" : "warning"}>{row.provided ? "Attached, unverified" : "Missing"}</Badge><span className="ml-2">{row.label}</span></li>)}</ul><p className="mt-3 text-xs text-fg-muted">An attachment’s category does not prove authenticity, fulfillment or delivery.</p></Panel>
      <Panel title="Grounded response drafts">
        {canWrite && <Button variant="secondary" busy={draft.isPending} onClick={() => draft.mutate()}>Prepare deterministic draft</Button>}
        {draft.error && <ErrorState error={draft.error} />}
        {detail.data.drafts.length === 0 && <p className="mt-3 text-sm text-fg-muted">No response draft prepared.</p>}
        <ul className="mt-3 space-y-4">{detail.data.drafts.map(d => <li key={d.id} className="rounded border border-line p-3"><p className="text-sm font-medium">{d.label}</p><p className="mt-2 whitespace-pre-wrap break-words text-sm text-fg-muted">{d.body}</p><a href={downloadUrl(`/disputes/${identity}/drafts/${d.id}/download`)} className="mt-3 inline-block text-sm text-accent hover:underline">Download private draft PDF</a></li>)}</ul>
      </Panel>
      <Panel title="Limitations and authorization"><ul className="list-disc space-y-2 pl-4 text-sm text-fg-muted">{detail.data.limitations.map(x => <li key={x}>{x}</li>)}</ul></Panel>
    </>}
  </div>;
}
