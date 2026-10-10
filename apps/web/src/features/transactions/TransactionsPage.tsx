import type { ColDef, ICellRendererParams, RowClickedEvent } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { sentinelGridTheme } from "@/components/transactions/grid-theme";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { DataOrigin, Transaction, TransactionStatus } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";

import { useTransactions } from "./useTransactions";

const STATUSES: TransactionStatus[] = ["ORDER_CREATED", "CAPTURE_PENDING", "CAPTURED", "CAPTURE_DECLINED", "CAPTURE_FAILED", "PARTIALLY_REFUNDED", "REFUNDED"];
const ORIGINS: DataOrigin[] = ["LIVE_SANDBOX", "SIMULATED", "SYNTHETIC_DEMO", "MERCHANT_PROVIDED"];
const PAGE_SIZE = 25;

export function TransactionsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const status = (params.get("status") ?? "") as TransactionStatus | "";
  const origin = (params.get("origin") ?? "") as DataOrigin | "";
  const page = Math.max(0, Number(params.get("page") ?? 0) || 0);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const q = useTransactions({ status, origin, q: params.get("q") ?? "", page, pageSize: PAGE_SIZE });

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setParams(next, { replace: true });
  };

  const columns = useMemo<ColDef<Transaction>[]>(
    () => [
      { headerName: "PayPal order", field: "paypal_order_id", minWidth: 170, cellClass: "font-mono text-xs", valueFormatter: (p) => p.value ?? "—" },
      { headerName: "Capture", field: "paypal_capture_id", minWidth: 160, cellClass: "font-mono text-xs", valueFormatter: (p) => p.value ?? "—" },
      { headerName: "Item", field: "product_name", minWidth: 150, valueFormatter: (p) => p.value ?? "—" },
      {
        headerName: "Amount",
        field: "amount_minor",
        type: "rightAligned",
        minWidth: 110,
        cellClass: "tabular",
        valueFormatter: (p) => (p.data ? formatMoney(p.data.amount_minor, p.data.currency) : ""),
      },
      { headerName: "Currency", field: "currency", minWidth: 100, maxWidth: 110 },
      { headerName: "Status", field: "status", minWidth: 150, cellRenderer: (p: ICellRendererParams<Transaction>) => (p.data ? <StatusBadge status={p.data.status} /> : null) },
      { headerName: "Risk", colId: "risk", minWidth: 110, sortable: false, valueGetter: () => "Not scored", cellClass: "text-fg-subtle", headerTooltip: "Risk scoring arrives in Phase 3; no score is shown until a real model produces one." },
      { headerName: "Origin", field: "data_origin", minWidth: 160, cellRenderer: (p: ICellRendererParams<Transaction>) => (p.data ? <OriginBadge origin={p.data.data_origin} /> : null) },
      { headerName: "Payment source", colId: "source", minWidth: 130, valueGetter: () => "PayPal" },
      { headerName: "Created", field: "created_at", minWidth: 150, sort: "desc", cellClass: "tabular", valueFormatter: (p) => formatDateTime(p.value) },
    ],
    [],
  );

  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader title="Transactions" description="Every PayPal order SENTINEL has created or reconciled. Select a row to open its record." />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <form
          role="search"
          className="relative min-w-56 flex-1 sm:max-w-sm"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: search });
          }}
        >
          <label htmlFor="txn-search" className="sr-only">Search by PayPal order or capture ID</label>
          <Search aria-hidden className="pointer-events-none absolute top-2.5 left-3 size-4 text-fg-subtle" />
          <input
            id="txn-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search order or capture ID"
            className="h-9 w-full rounded-md border border-line-strong bg-sunken pr-3 pl-9 text-sm placeholder:text-fg-subtle focus:border-accent focus:outline-none"
          />
        </form>
        <Select label="Status" value={status} onChange={(v) => update({ status: v })} options={STATUSES.map((s) => [s, humanize(s)])} />
        <Select label="Origin" value={origin} onChange={(v) => update({ origin: v })} options={ORIGINS.map((o) => [o, humanize(o)])} />
      </div>

      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && q.data.total === 0 && !q.isFetching ? (
        <div className="rounded-lg border border-line bg-surface">
          <EmptyState
            title={status || origin || params.get("q") ? "No transactions match these filters" : "No transactions yet"}
            action={<Button variant="secondary" onClick={() => navigate("/checkout")}>Open sandbox checkout</Button>}
          >
            Transactions appear once an order is created through PayPal.
          </EmptyState>
        </div>
      ) : (
        <div className="sentinel-grid w-full">
          <AgGridReact<Transaction>
            theme={sentinelGridTheme}
            rowData={q.data?.items}
            columnDefs={columns}
            defaultColDef={{ sortable: true, resizable: true, flex: 1 }}
            loading={q.isPending}
            getRowId={(p) => p.data.id}
            onRowClicked={(e: RowClickedEvent<Transaction>) => e.data && navigate(`/transactions/${e.data.id}`)}
            onCellKeyDown={(e) => {
              const ke = e.event as KeyboardEvent | undefined;
              if (ke?.key === "Enter" && e.data) navigate(`/transactions/${e.data.id}`);
            }}
            domLayout="autoHeight"
            rowHeight={42}
            headerHeight={38}
            suppressCellFocus={false}
          />
        </div>
      )}

      <nav aria-label="Pagination" className="mt-3 flex items-center justify-between text-sm text-fg-muted">
        <p className="tabular">
          {total === 0 ? "0 results" : `${page * PAGE_SIZE + 1}–${Math.min(total, (page + 1) * PAGE_SIZE)} of ${total}`}
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

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  const id = `filter-${label.toLowerCase()}`;
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
