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
import { api, type DataOrigin } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";

type Refund = {
  id: string;
  case_id: string;
  transaction_id: string;
  amount_minor: number;
  currency: string;
  data_origin: DataOrigin;
  status: string;
  requested_by_user_id: string;
  snapshot_sha256: string;
  submission_started: boolean;
  provider_refund_id: string | null;
  provider_status: string | null;
  error_category: string | null;
  created_at: string;
};

export function RefundsPage() {
  const me = useMe();
  const client = useQueryClient();
  const q = useQuery({
    queryKey: ["refunds"],
    queryFn: () => api<Refund[]>("/refunds"),
  });
  const [params] = useSearchParams();
  const [caseId, setCaseId] = useState(params.get("case") ?? "");
  const [amount, setAmount] = useState("");
  const request = useMutation({
    mutationFn: () =>
      api<Refund>(`/cases/${caseId}/refunds`, {
        method: "POST",
        body: { amount_minor: amount === "" ? null : Number(amount) },
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["refunds"] });
      setAmount("");
    },
  });
  return (
    <>
      <PageHeader
        title="Refund review"
        description="Request and independently approve full or partial refunds. Approval never executes a financial action. Sandbox execution is disabled by default."
      />
      <Panel title="Financial safety">
        <p className="text-sm text-fg-muted">
          Amounts are integer minor units in the payment’s currency. Pending and
          ambiguous requests reserve their amount. A timeout is not a failed
          refund and must be reconciled before another submission.
        </p>
        <p className="mt-2 text-sm text-fg-muted">
          Genuine provider execution is not performed by this demonstration.
          Synthetic and simulated requests cannot execute against PayPal.
        </p>
      </Panel>
      {(me.data?.role === "ADMIN" || me.data?.role === "ANALYST") && (
        <Panel title="Prepare refund request" className="mt-4">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              request.mutate();
            }}
            className="flex flex-wrap items-end gap-3"
          >
            <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
              Case UUID
              <input
                aria-label="Case UUID"
                required
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                className="rounded border border-line bg-raised p-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Partial amount (minor units)
              <input
                aria-label="Partial amount (minor units)"
                type="number"
                min="1"
                step="1"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="Blank = available full balance"
                className="rounded border border-line bg-raised p-2"
              />
            </label>
            <Button type="submit" busy={request.isPending}>
              Request independent approval
            </Button>
          </form>
          {request.isError && <ErrorState error={request.error} />}
        </Panel>
      )}
      <div className="mt-4 space-y-4">
        {q.isPending && <Skeleton className="h-40" />}
        {q.isError && (
          <ErrorState error={q.error} onRetry={() => void q.refetch()} />
        )}
        {q.data?.length === 0 && (
          <EmptyState title="No refund requests">
            Use a case to prepare an amount for independent review. Existing
            Phase 4 refund intents remain in the case’s approval history.
          </EmptyState>
        )}
        {q.data?.map((refund) => (
          <RefundCard key={refund.id} refund={refund} />
        ))}
      </div>
    </>
  );
}

function RefundCard({ refund }: { refund: Refund }) {
  const me = useMe();
  const client = useQueryClient();
  const decision = useMutation({
    mutationFn: (choice: "APPROVED" | "REJECTED") =>
      api<Refund>(`/refunds/${refund.id}/decision`, {
        method: "POST",
        body: { decision: choice, snapshot_sha256: refund.snapshot_sha256 },
      }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ["refunds"] }),
  });
  const canDecide =
    me.data?.role === "ADMIN" &&
    me.data.id !== refund.requested_by_user_id &&
    refund.status === "PENDING_APPROVAL";
  return (
    <Panel
      title={`${formatMoney(refund.amount_minor, refund.currency)} · ${humanize(refund.status)}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <OriginBadge origin={refund.data_origin} />
        <Badge tone={refund.status === "SUCCEEDED" ? "positive" : "neutral"}>
          {humanize(refund.status)}
        </Badge>
        <Link
          to={`/app/cases/${refund.case_id}`}
          className="text-sm text-accent hover:underline"
        >
          Open case
        </Link>
      </div>
      <p className="mt-2 text-xs text-fg-muted">
        Requested {formatDateTime(refund.created_at)} · Provider submission{" "}
        {refund.submission_started
          ? "may have started; inspect durable outcome"
          : "not started"}
      </p>
      <p className="mt-2 break-all font-mono text-xs text-fg-subtle">
        Snapshot SHA-256: {refund.snapshot_sha256}
      </p>
      {refund.provider_refund_id && (
        <p className="mt-2 text-sm">
          Provider refund: {refund.provider_refund_id} ·{" "}
          {refund.provider_status}
        </p>
      )}
      {refund.error_category && (
        <p className="mt-2 text-sm text-warning">
          {humanize(refund.error_category)}
        </p>
      )}
      {canDecide && (
        <div className="mt-3 flex gap-2">
          <Button
            busy={decision.isPending}
            onClick={() => decision.mutate("APPROVED")}
          >
            Approve intent
          </Button>
          <Button
            variant="secondary"
            disabled={decision.isPending}
            onClick={() => decision.mutate("REJECTED")}
          >
            Reject
          </Button>
        </div>
      )}
      {decision.isError && <ErrorState error={decision.error} />}
      {refund.status === "APPROVED" && (
        <p className="mt-3 text-sm text-fg-muted">
          Approved intent. Financial execution requires a separately enabled
          sandbox runtime and an administrator’s exact snapshot confirmation
          through the protected API.
        </p>
      )}
    </Panel>
  );
}
