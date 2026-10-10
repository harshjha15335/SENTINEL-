import { clsx } from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import type { Case, CasePriority, CaseStatus, DataOrigin } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";

import { isOverdue, PRIORITY_TONE, RESOLUTION_LABEL, STATUS_LABEL, STATUS_TONE } from "./labels";
import { useCases } from "./useCases";

const PAGE_SIZE = 25;
const TABS: { value: CaseStatus | ""; label: string }[] = [
  { value: "OPEN", label: "Open" },
  { value: "IN_REVIEW", label: "In review" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "", label: "All" },
];
const PRIORITIES: CasePriority[] = ["HIGH", "MEDIUM", "LOW"];
const ORIGINS: DataOrigin[] = ["LIVE_SANDBOX", "SIMULATED", "SYNTHETIC_DEMO", "MERCHANT_PROVIDED"];

export function CasesPage() {
  const [params, setParams] = useSearchParams();
  const status = (params.has("status") ? params.get("status") : "OPEN") as CaseStatus | "";
  const priority = (params.get("priority") ?? "") as CasePriority | "";
  const origin = (params.get("origin") ?? "") as DataOrigin | "";
  const mine = params.get("mine") === "1";
  const page = Math.max(0, Number(params.get("page") ?? 0) || 0);
  const q = useCases({ status, priority, origin, mine, page, pageSize: PAGE_SIZE });

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v || k === "status") next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setParams(next, { replace: true });
  };

  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Payments the risk model placed in the high band, plus cases analysts opened by hand. Highest priority and earliest due first."
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="Case status" className="flex rounded-md border border-line-strong bg-sunken p-0.5">
          {TABS.map((t) => (
            <button
              key={t.label}
              role="tab"
              aria-selected={status === t.value}
              onClick={() => update({ status: t.value })}
              className={clsx(
                "h-8 rounded-[5px] px-3 text-sm whitespace-nowrap",
                status === t.value ? "bg-raised text-fg" : "text-fg-muted hover:text-fg",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <Select label="Priority" value={priority} onChange={(v) => update({ priority: v })} options={PRIORITIES.map((p) => [p, humanize(p)])} />
        <Select label="Origin" value={origin} onChange={(v) => update({ origin: v })} options={ORIGINS.map((o) => [o, humanize(o)])} />
        <label className="flex h-9 items-center gap-2 text-sm text-fg-muted">
          <input type="checkbox" checked={mine} onChange={(e) => update({ mine: e.target.checked ? "1" : "" })} className="size-4 accent-[var(--color-accent)]" />
          Assigned to me
        </label>
      </div>

      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      <div className="rounded-lg border border-line bg-surface">
        {q.isPending && (
          <div className="space-y-2 p-4" aria-busy="true" aria-label="Loading cases">
            {Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-14" />)}
          </div>
        )}
        {q.data && q.data.items.length === 0 && (
          <EmptyState title={status === "OPEN" && !priority && !origin && !mine ? "Nothing waiting for review" : "No cases match these filters"}>
            High-risk payments open a case automatically when they are scored.
          </EmptyState>
        )}
        {q.data && q.data.items.length > 0 && (
          <ul className="divide-y divide-line" aria-label="Cases">
            {q.data.items.map((c) => <CaseRow key={c.id} c={c} />)}
          </ul>
        )}
      </div>

      <nav aria-label="Pagination" className="mt-3 flex items-center justify-between text-sm text-fg-muted">
        <p className="tabular">
          {total === 0 ? "0 cases" : `${page * PAGE_SIZE + 1}–${Math.min(total, (page + 1) * PAGE_SIZE)} of ${total}`}
        </p>
        <div className="flex gap-1">
          <Button variant="ghost" iconOnly aria-label="Previous page" disabled={page === 0} onClick={() => update({ page: String(page - 1) })}>
            <ChevronLeft className="size-4" />
          </Button>
          <Button variant="ghost" iconOnly aria-label="Next page" disabled={page + 1 >= pages} onClick={() => update({ page: String(page + 1) })}>
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </nav>
    </>
  );
}

function CaseRow({ c }: { c: Case }) {
  const overdue = isOverdue(c.due_at, c.status);
  const t = c.transaction;
  return (
    <li>
      <Link to={`/cases/${c.id}`} className="grid gap-2 px-4 py-3 hover:bg-raised focus-visible:bg-raised md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-center md:gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={PRIORITY_TONE[c.priority]}>{c.priority.toLowerCase()}</Badge>
            <Badge tone={STATUS_TONE[c.status]}>{c.resolution ? RESOLUTION_LABEL[c.resolution] : STATUS_LABEL[c.status]}</Badge>
            <span className="truncate text-sm font-medium text-fg">{c.title}</span>
          </div>
          <p className="mt-1 truncate text-xs text-fg-subtle">
            {t.product_name ?? "Payment"} · {t.payer_reference ?? "no payer reference"} · {humanize(c.source)}
          </p>
        </div>
        <div className="flex items-center gap-3 md:block">
          <p className="tabular text-sm">{formatMoney(t.amount_minor, t.currency)}</p>
          {t.risk_band && <RiskBadge band={t.risk_band} score={t.risk_score} />}
        </div>
        <div><OriginBadge origin={c.data_origin} /></div>
        <div className="text-xs md:text-right">
          <p className={clsx("tabular", overdue ? "font-medium text-critical" : "text-fg-muted")}>
            {c.status === "RESOLVED" ? `Resolved ${formatDateTime(c.resolved_at)}` : `${overdue ? "Overdue since" : "Due"} ${formatDateTime(c.due_at)}`}
          </p>
          <p className="mt-0.5 truncate text-fg-subtle">{c.assignee ? c.assignee.email : "Unassigned"}</p>
        </div>
      </Link>
    </li>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  const id = `case-filter-${label.toLowerCase()}`;
  return (
    <div className="flex items-center gap-2">
      <label htmlFor={id} className="text-sm text-fg-muted">{label}</label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-line-strong bg-sunken px-2.5 text-sm text-fg focus:border-accent focus:outline-none"
      >
        <option value="">All</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </div>
  );
}
