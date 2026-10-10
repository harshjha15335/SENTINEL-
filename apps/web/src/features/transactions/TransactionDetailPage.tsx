import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TransactionCases } from "@/features/cases/TransactionCases";
import { RiskPanel } from "@/features/risk/RiskPanel";
import type { TransactionDetail } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";

import { useTransaction } from "./useTransactions";

export function TransactionDetailPage() {
  const { id = "" } = useParams();
  const q = useTransaction(id);
  return (
    <>
      <Link to="/transactions" className="mb-4 inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg">
        <ArrowLeft aria-hidden className="size-4" /> Transactions
      </Link>
      {q.isPending && <Skeleton className="h-72" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && <Detail t={q.data} />}
    </>
  );
}

const ACTION_LABELS: Record<string, string> = {
  "paypal.order.created": "PayPal order created",
  "paypal.order.captured": "Capture response recorded",
  "paypal.order.capture_failed": "Capture failed",
  "paypal.webhook.status_applied": "Status updated from verified webhook",
  "risk.assessment.created": "Risk assessment recorded (model-generated)",
};

type TimelineItem = { at: string; label: string; detail?: string; source: "SENTINEL" | "PayPal webhook" };

function timeline(t: TransactionDetail): TimelineItem[] {
  const items: TimelineItem[] = t.audit.map((a) => ({
    at: a.created_at,
    label: ACTION_LABELS[a.action] ?? humanize(a.action.replaceAll(".", "_")),
    detail: a.actor_type === "PAYPAL_WEBHOOK" ? `${String(a.metadata["from"] ?? "")} → ${String(a.metadata["to"] ?? "")}` : undefined,
    source: a.actor_type === "PAYPAL_WEBHOOK" ? "PayPal webhook" : "SENTINEL",
  }));
  for (const e of t.events) {
    items.push({
      at: e.received_at,
      label: e.provider_event_type,
      detail: `${humanize(e.verification_status)} · ${humanize(e.processing_status)}${e.delivery_count > 1 ? ` · delivered ${e.delivery_count}×` : ""}`,
      source: "PayPal webhook",
    });
  }
  return items.sort((a, b) => a.at.localeCompare(b.at));
}

function Detail({ t }: { t: TransactionDetail }) {
  return (
    <>
      <PageHeader
        title={formatMoney(t.amount_minor, t.currency)}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={t.status} />
            <OriginBadge origin={t.data_origin} />
            <span>{t.product_name ?? "Unknown item"} × {t.quantity}</span>
          </span>
        }
      />
      {t.failure_reason && (
        <div role="alert" className="mb-4 rounded-md border border-critical/40 bg-critical-soft px-3 py-2 text-sm text-fg">
          {t.failure_reason}
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="PayPal references" className="lg:col-span-2">
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <Field label="Order ID" mono value={t.paypal_order_id} />
            <Field label="Capture ID" mono value={t.paypal_capture_id} />
            <Field label="Provider status" value={t.provider_status} />
            <Field label="Payer reference" mono value={t.payer_reference} hint="PayPal payer ID. SENTINEL does not store buyer email or name." />
            <Field label={t.data_origin === "SYNTHETIC_DEMO" ? "Occurred at (synthetic)" : "Captured at"} value={formatDateTime(t.occurred_at)} />
            <Field label="SENTINEL record" mono value={t.id} />
          </dl>
        </Panel>
        <RiskPanel
          transactionId={t.id}
          scorable={t.occurred_at != null}
          className="lg:row-span-2"
          caseSlot={<TransactionCases transactionId={t.id} />}
        />
        <Panel title="Event timeline" className="lg:col-span-2">
          <ol className="relative ml-1 border-l border-line">
            {timeline(t).map((item, i) => (
              <li key={i} className="relative pb-4 pl-5 last:pb-0">
                <span aria-hidden className="absolute top-1.5 -left-[5px] size-2.5 rounded-full border-2 border-surface bg-accent" />
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="tabular text-xs text-fg-subtle">{formatDateTime(item.at)}</p>
                  <span className="text-[11px] tracking-wide text-fg-subtle uppercase">{item.source}</span>
                </div>
                {item.detail && <p className="mt-0.5 text-xs text-fg-muted">{item.detail}</p>}
              </li>
            ))}
          </ol>
        </Panel>
      </div>
    </>
  );
}

function Field({ label, value, mono, hint }: { label: string; value: string | null | undefined; mono?: boolean; hint?: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-fg-subtle" title={hint}>{label}</dt>
      <dd className={`mt-0.5 truncate text-sm ${mono ? "font-mono text-[13px]" : ""}`}>{value || "—"}</dd>
    </div>
  );
}
