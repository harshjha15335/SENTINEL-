import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { api, type DataOrigin, type Schemas } from "@/lib/api";
import { formatDateTime, humanize } from "@/lib/format";

type Network = Schemas["NetworkOut"];
type Node = Schemas["GraphNode"];
const ORIGINS: DataOrigin[] = ["SYNTHETIC_DEMO", "SIMULATED", "LIVE_SANDBOX", "MERCHANT_PROVIDED"];

export function NetworkPage() {
  const [origin, setOrigin] = useState<DataOrigin>("SYNTHETIC_DEMO");
  const [days, setDays] = useState(90);
  const [limit, setLimit] = useState(12);
  const [payer, setPayer] = useState("");
  const [band, setBand] = useState("");
  const [relationship, setRelationship] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["network", origin, days, limit, payer, band], queryFn: () => api<Network>(`/network?data_origin=${origin}&days=${days}&limit=${limit}${payer ? `&payer=${encodeURIComponent(payer)}` : ""}${band ? `&risk_band=${band}` : ""}`) });
  return <>
    <PageHeader title="Relationship explorer" description="Explore recorded payer, payment and case links within your merchant. Connections are investigation context, not proof of identity or coordinated fraud." />
    <div className="mb-4 flex flex-wrap items-end gap-4">
      <label className="text-sm">Data origin<select aria-label="Network data origin" value={origin} onChange={e => { setOrigin(e.target.value as DataOrigin); setSelected(null); }} className="mt-1 block rounded border border-line bg-surface p-2">{ORIGINS.map(o => <option value={o} key={o}>{humanize(o)}</option>)}</select></label>
      <label className="text-sm">Window<select aria-label="Network window" value={days} onChange={e => setDays(Number(e.target.value))} className="mt-1 block rounded border border-line bg-surface p-2">{[7, 30, 90, 180, 365].map(n => <option key={n} value={n}>{n} days</option>)}</select></label>
      <label className="text-sm">Payment limit<select aria-label="Network payment limit" value={limit} onChange={e => setLimit(Number(e.target.value))} className="mt-1 block rounded border border-line bg-surface p-2">{[12, 30, 60].map(n => <option value={n} key={n}>{n}</option>)}</select></label>
      <label className="text-sm">Risk band<select aria-label="Network risk band" value={band} onChange={e => setBand(e.target.value)} className="mt-1 block rounded border border-line bg-surface p-2">{["", "HIGH", "MEDIUM", "LOW"].map(b => <option value={b} key={b}>{b || "Any scored or unscored"}</option>)}</select></label>
      <label className="text-sm">Relationship<select aria-label="Relationship type" value={relationship} onChange={e => setRelationship(e.target.value)} className="mt-1 block rounded border border-line bg-surface p-2"><option value="all">All</option><option value="recorded_payer">Recorded payer</option><option value="review_case">Review case</option><option value="owns">Merchant ownership</option></select></label>
      <label className="text-sm">Exact payer reference<input aria-label="Exact payer reference" value={payer} maxLength={64} onChange={e => { setPayer(e.target.value); setSelected(null); }} className="mt-1 block max-w-full rounded border border-line bg-surface p-2" placeholder="Optional recorded reference" /></label>
    </div>
    {q.isPending && <Skeleton className="h-64" />}
    {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
    {q.data && <>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-sm text-fg-muted"><OriginBadge origin={q.data.data_origin} /><span>{q.data.transaction_count} payments · {q.data.repeated_payer_groups} payer references seen at least 3 times in this view</span></div>
      <p className="mb-4 text-xs text-fg-muted">{formatDateTime(q.data.window.start)} to {formatDateTime(q.data.window.end)} (exclusive end). This pattern count describes the bounded view, not a fraud classification.</p>
      {q.data.truncated && <p role="alert" className="mb-4 text-sm text-warning">View truncated. Narrow the window or filter an exact payer reference to inspect more relevant records.</p>}
      {q.data.transaction_count === 0 ? <Panel title="Relationships"><EmptyState title="No payments in this origin and window" /></Panel> : <>
        <Panel title="Recorded relationships"><Diagram data={{ ...q.data, edges: q.data.edges.filter(e => relationship === "all" || e.relationship === relationship) }} selected={selected} /><p className="mt-2 text-xs text-fg-muted">Select a record below to highlight its direct connections. Lines are explained in the edge inventory.</p></Panel>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title="Explore records"><ul className="max-h-80 space-y-2 overflow-y-auto text-sm">{q.data.nodes.map(node => <li key={node.id} className="flex flex-wrap items-center gap-2"><button aria-pressed={selected === node.id} className="rounded border border-line px-2 py-1 text-left hover:bg-raised" onClick={() => setSelected(selected === node.id ? null : node.id)}>{humanize(node.kind)}: {node.label}</button>{recordLink(node)}{node.risk_band && <span className="text-xs text-fg-muted">{node.risk_band}</span>}</li>)}</ul></Panel>
          <Panel title="Connection evidence"><ul className="max-h-80 space-y-3 overflow-y-auto text-sm">{q.data.edges.filter(edge => (relationship === "all" || edge.relationship === relationship) && (!selected || edge.source === selected || edge.target === selected)).map(edge => <li key={`${edge.source}-${edge.target}`} className="border-b border-line pb-2"><p className="font-medium">{humanize(edge.relationship)}</p><p className="mt-1 text-xs text-fg-muted">{edge.explanation}</p><Link className="mt-1 inline-block text-xs text-accent hover:underline" to={`/transactions/${edge.transaction_id}`}>Open source payment</Link></li>)}</ul></Panel>
        </div>
      </>}
      <Panel title="Provenance and limits" className="mt-4"><ul className="list-disc space-y-1 pl-5 text-xs text-fg-muted">{q.data.limitations.map(note => <li key={note}>{note}</li>)}</ul></Panel>
    </>}
  </>;
}

function recordLink(node: Node) {
  if (!node.record_id) return null;
  const route = node.kind === "transaction" ? "transactions" : node.kind === "case" ? "cases" : null;
  return route ? <Link className="text-xs text-accent hover:underline" to={`/${route}/${node.record_id}`}>Open record</Link> : null;
}

function Diagram({ data, selected }: { data: Network; selected: string | null }) {
  const columns = ["merchant", "payer", "transaction", "case"];
  const max = Math.max(...columns.map(kind => data.nodes.filter(n => n.kind === kind).length), 1);
  const height = Math.max(300, max * 40 + 60);
  const points = new Map<string, { x: number; y: number }>();
  columns.forEach((kind, column) => {
    const nodes = data.nodes.filter(n => n.kind === kind);
    nodes.forEach((node, i) => points.set(node.id, { x: 110 + column * 220, y: 50 + (i + 0.5) * (height - 80) / Math.max(1, nodes.length) }));
  });
  return <div tabIndex={0} role="region" aria-label="Relationship diagram" className="max-h-[480px] overflow-auto rounded border border-line bg-sunken"><svg aria-hidden viewBox={`0 0 900 ${height}`} className="min-w-[900px]" style={{ height, width: "100%" }}>
    {columns.map((kind, i) => <text key={kind} x={110 + i * 220} y={25} textAnchor="middle" fill="currentColor" fontSize="12">{humanize(kind)}</text>)}
    {data.edges.map(edge => {
      const a = points.get(edge.source), b = points.get(edge.target);
      if (!a || !b) return null;
      const active = !selected || edge.source === selected || edge.target === selected;
      return <line key={`${edge.source}-${edge.target}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="currentColor" opacity={active ? 0.4 : 0.06} strokeWidth={active && selected ? 2 : 1} />;
    })}
    {data.nodes.map(node => {
      const p = points.get(node.id);
      if (!p) return null;
      return <g key={node.id}><circle cx={p.x} cy={p.y} r={selected === node.id ? 10 : 7} fill={node.risk_band === "HIGH" ? "#ef6262" : node.kind === "payer" ? "#e5b454" : "#57b7be"} /><text x={p.x + 12} y={p.y + 4} fill="currentColor" fontSize="10">{node.label.slice(0, 22)}</text></g>;
    })}
  </svg></div>;
}
