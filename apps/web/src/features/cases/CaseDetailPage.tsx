import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { useMe } from "@/features/auth/session";
import { ApprovalsPanel } from "@/features/investigation/ApprovalsPanel";
import { ChecklistPanel, EvidencePanel } from "@/features/investigation/EvidencePanel";
import { InvestigationPanel } from "@/features/investigation/InvestigationPanel";
import { PacketPanel } from "@/features/investigation/PacketPanel";
import { RiskPanel } from "@/features/risk/RiskPanel";
import { isOperator, type CaseDetail, type CaseResolution } from "@/lib/api";
import { formatDateTime, formatMoney, humanize } from "@/lib/format";

import { isOverdue, PRIORITY_TONE, RESOLUTION_HELP, RESOLUTION_LABEL, STATUS_LABEL, STATUS_TONE } from "./labels";
import { useAddNote, useCase, useClaimCase, useResolveCase } from "./useCases";

export function CaseDetailPage() {
  const { id = "" } = useParams();
  const q = useCase(id);
  return (
    <>
      <Link to="/cases" className="mb-4 inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg">
        <ArrowLeft aria-hidden className="size-4" /> Review queue
      </Link>
      {q.isPending && <Skeleton className="h-72" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && <Detail c={q.data} />}
    </>
  );
}

const ACTION_LABELS: Record<string, string> = {
  "case.opened": "Case opened",
  "case.claimed": "Claimed for review",
  "case.note_added": "Note added",
  "case.resolved": "Case resolved",
  "investigation.requested": "Investigation requested",
  "investigation.completed": "Investigation completed",
  "investigation.failed": "Investigation failed",
  "evidence.uploaded": "Evidence uploaded",
  "evidence.downloaded": "Evidence downloaded",
  "packet.generated": "Evidence packet generated",
  "packet.downloaded": "Evidence packet downloaded",
  "approval.requested": "Approval requested",
  "approval.approved": "Approval granted",
  "approval.rejected": "Approval rejected",
  "action.execution_recorded": "Approved action recorded (no payment executed)",
};

function Detail({ c }: { c: CaseDetail }) {
  const t = c.transaction;
  const me = useMe();
  const operator = isOperator(me.data?.role);
  const overdue = isOverdue(c.due_at, c.status);
  return (
    <>
      <PageHeader
        title={c.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>
            <Badge tone={PRIORITY_TONE[c.priority]}>{c.priority.toLowerCase()} priority</Badge>
            <OriginBadge origin={c.data_origin} />
            <span className="text-fg-subtle">Investigation workbench ·</span>
            <span className={overdue ? "text-critical" : undefined}>
              {c.status === "RESOLVED" ? `Resolved ${formatDateTime(c.resolved_at)}` : `${overdue ? "Overdue since" : "Due"} ${formatDateTime(c.due_at)}`}
            </span>
          </span>
        }
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Panel
            title="Payment"
            actions={<Link to={`/transactions/${t.id}`} className="text-sm text-accent hover:underline">Open payment</Link>}
          >
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-3">
              <Field label="Amount" value={formatMoney(t.amount_minor, t.currency)} />
              <Field label="Status" value={<StatusBadge status={t.status} />} />
              <Field label="Item" value={`${t.product_name ?? "Unknown item"} × ${t.quantity}`} />
              <Field label="Payer reference" value={<span className="font-mono text-[13px]">{t.payer_reference ?? "—"}</span>} />
              <Field label="Occurred" value={formatDateTime(t.occurred_at)} />
              <Field label="Opened by" value={humanize(c.source)} />
              <Field label="PayPal order" value={<span className="font-mono text-[13px]">{t.paypal_order_id ?? "—"}</span>} />
              <Field label="PayPal capture" value={<span className="font-mono text-[13px]">{t.paypal_capture_id ?? "—"}</span>} />
              <Field label="Data origin" value={<OriginBadge origin={t.data_origin} />} />
            </dl>
          </Panel>
          <RiskPanel transactionId={t.id} scorable={t.occurred_at != null} />
          <InvestigationPanel caseId={c.id} canRun={operator} />
          <EvidencePanel caseId={c.id} canUpload={operator} />
        </div>
        <div className="space-y-4">
          <Actions c={c} />
          <ApprovalsPanel caseId={c.id} me={me.data} canRequest={operator} resolved={c.status === "RESOLVED"} />
          <PacketPanel caseId={c.id} canGenerate={operator} />
          <ChecklistPanel caseId={c.id} />
          <Notes c={c} />
          <Panel title="Activity">
            {c.audit.length === 0 && <p className="text-sm text-fg-muted">No activity recorded yet.</p>}
            <ol className="space-y-2">
              {c.audit.map((a) => (
                <li key={a.id} className="border-l border-line pl-3 text-sm">
                  <p>{ACTION_LABELS[a.action] ?? a.action}</p>
                  <p className="tabular text-xs text-fg-subtle">
                    {formatDateTime(a.created_at)} · {a.actor_type === "SYSTEM" ? "SENTINEL" : "Team member"}
                  </p>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </>
  );
}

function Actions({ c }: { c: CaseDetail }) {
  const me = useMe();
  const claim = useClaimCase(c.id);
  const resolve = useResolveCase(c.id);
  const toast = useToast();
  const [resolution, setResolution] = useState<CaseResolution | "">("");
  const [note, setNote] = useState("");

  if (c.status === "RESOLVED") {
    return (
      <Panel title="Outcome">
        <p className="text-sm font-medium">{c.resolution ? RESOLUTION_LABEL[c.resolution] : "Resolved"}</p>
        {c.resolution_note && <p className="mt-1 text-sm whitespace-pre-wrap text-fg-muted">{c.resolution_note}</p>}
        <p className="mt-2 text-xs text-fg-subtle">{c.assignee ? `By ${c.assignee.email}` : null}</p>
      </Panel>
    );
  }

  const operator = isOperator(me.data?.role);
  const mine = c.assignee?.id === me.data?.id;
  const free = c.assignee == null;
  const fail = (title: string) => (e: Error) => toast.notify({ tone: "critical", title, body: e.message });

  return (
    <Panel title="Decision">
      <p className="text-sm text-fg-muted">
        {c.assignee ? <>Assigned to <span className="text-fg">{c.assignee.email}</span>.</> : "Nobody has claimed this case yet."}
      </p>
      {!operator && <p className="mt-2 text-sm text-fg-subtle">Your role can view cases but not change them.</p>}
      {operator && free && (
        <Button className="mt-3" variant="secondary" busy={claim.isPending} onClick={() => claim.mutate(undefined, { onError: fail("Could not claim case") })}>
          Claim for review
        </Button>
      )}
      {operator && (mine || free) && (
        <form
          className="mt-4 space-y-3 border-t border-line pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!resolution) return;
            resolve.mutate(
              { resolution, note: note.trim() },
              {
                onSuccess: () => toast.notify({ tone: "positive", title: "Case resolved", body: "Your conclusion is recorded. No payment was changed." }),
                onError: fail("Could not resolve case"),
              },
            );
          }}
        >
          <fieldset>
            <legend className="text-sm font-medium">Conclusion</legend>
            <div className="mt-2 space-y-2">
              {(Object.keys(RESOLUTION_LABEL) as CaseResolution[]).map((r) => (
                <label key={r} className="flex cursor-pointer items-start gap-2.5 rounded-md border border-line px-3 py-2 has-[:checked]:border-accent">
                  <input type="radio" name="resolution" value={r} checked={resolution === r} onChange={() => setResolution(r)} className="mt-1 accent-[var(--color-accent)]" />
                  <span>
                    <span className="block text-sm">{RESOLUTION_LABEL[r]}</span>
                    <span className="block text-xs text-fg-subtle">{RESOLUTION_HELP[r]}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <div>
            <label htmlFor="resolution-note" className="text-sm font-medium">Reasoning</label>
            <textarea
              id="resolution-note"
              required
              minLength={3}
              maxLength={4000}
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="mt-1 w-full rounded-md border border-line-strong bg-sunken px-3 py-2 text-sm focus:border-accent focus:outline-none"
            />
          </div>
          <p className="text-xs text-fg-subtle">Resolving records your conclusion. It does not refund, block or contact anyone.</p>
          <Button type="submit" busy={resolve.isPending} disabled={!resolution || note.trim().length < 3}>
            Resolve case
          </Button>
        </form>
      )}
    </Panel>
  );
}

function Notes({ c }: { c: CaseDetail }) {
  const me = useMe();
  const add = useAddNote(c.id);
  const toast = useToast();
  const [body, setBody] = useState("");
  return (
    <Panel title={`Notes (${c.notes.length})`}>
      {c.notes.length === 0 && <p className="text-sm text-fg-muted">No notes yet.</p>}
      <ul className="space-y-3">
        {c.notes.map((n) => (
          <li key={n.id} className="text-sm">
            <p className="whitespace-pre-wrap">{n.body}</p>
            <p className="tabular mt-0.5 text-xs text-fg-subtle">
              {n.author?.email ?? "Unknown"} · {formatDateTime(n.created_at)}
            </p>
          </li>
        ))}
      </ul>
      {isOperator(me.data?.role) && (
        <form
          className="mt-3 flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate(body.trim(), {
              onSuccess: () => setBody(""),
              onError: (err) => toast.notify({ tone: "critical", title: "Note not saved", body: err.message }),
            });
          }}
        >
          <label htmlFor="case-note" className="sr-only">Add a note</label>
          <textarea
            id="case-note"
            rows={2}
            maxLength={4000}
            placeholder="Add a note for the next analyst"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            className="w-full rounded-md border border-line-strong bg-sunken px-3 py-2 text-sm placeholder:text-fg-subtle focus:border-accent focus:outline-none"
          />
          <Button type="submit" variant="secondary" className="self-start" busy={add.isPending} disabled={!body.trim()}>
            Add note
          </Button>
        </form>
      )}
    </Panel>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-fg-subtle">{label}</dt>
      <dd className="mt-0.5 truncate text-sm">{value}</dd>
    </div>
  );
}
