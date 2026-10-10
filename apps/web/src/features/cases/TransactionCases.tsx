import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useMe } from "@/features/auth/session";
import { isOperator } from "@/lib/api";

import { STATUS_LABEL, STATUS_TONE } from "./labels";
import { useCases, useOpenCase } from "./useCases";

/** Case status for one payment, with a way to open a manual review. */
export function TransactionCases({ transactionId }: { transactionId: string }) {
  const q = useCases({ transactionId, page: 0, pageSize: 5 });
  const me = useMe();
  const open = useOpenCase();
  const toast = useToast();
  const navigate = useNavigate();
  const [reason, setReason] = useState("");
  const [composing, setComposing] = useState(false);

  if (!q.data) return null;
  const active = q.data.items.find((c) => c.status !== "RESOLVED");
  const resolved = q.data.items.filter((c) => c.status === "RESOLVED");

  return (
    <div className="mt-4 border-t border-line pt-4">
      <h3 className="text-xs font-medium tracking-wide text-fg-subtle uppercase">Review</h3>
      {active ? (
        <p className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <Badge tone={STATUS_TONE[active.status]}>{STATUS_LABEL[active.status]}</Badge>
          <Link to={`/cases/${active.id}`} className="text-accent hover:underline">{active.title}</Link>
        </p>
      ) : (
        <p className="mt-2 text-sm text-fg-muted">No open case for this payment.</p>
      )}
      {resolved.map((c) => (
        <p key={c.id} className="mt-1 text-xs text-fg-subtle">
          Earlier case <Link to={`/cases/${c.id}`} className="text-accent underline underline-offset-2">resolved</Link>
        </p>
      ))}
      {!active && isOperator(me.data?.role) && !composing && (
        <Button variant="secondary" className="mt-3" onClick={() => setComposing(true)}>
          Open a review case
        </Button>
      )}
      {!active && composing && (
        <form
          className="mt-3 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            open.mutate(
              { transactionId, reason: reason.trim() },
              {
                onSuccess: (c) => navigate(`/cases/${c.id}`),
                onError: (err) => toast.notify({ tone: "critical", title: "Could not open case", body: err.message }),
              },
            );
          }}
        >
          <label htmlFor="case-reason" className="text-sm text-fg-muted">Why does this payment need review?</label>
          <textarea
            id="case-reason"
            required
            minLength={3}
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-line-strong bg-sunken px-3 py-2 text-sm focus:border-accent focus:outline-none"
          />
          <div className="flex gap-2">
            <Button type="submit" busy={open.isPending} disabled={reason.trim().length < 3}>Open case</Button>
            <Button type="button" variant="ghost" onClick={() => setComposing(false)}>Cancel</Button>
          </div>
        </form>
      )}
    </div>
  );
}
