import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import type { ApprovalActionType, ApprovalRequest, Me } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";

import { APPROVAL_ACTION, APPROVAL_STATUS, INPUT } from "./labels";
import { useApprovals, useCreateApproval, useDecideApproval, usePackets } from "./useWorkbench";

type Props = { caseId: string; me: Me | null | undefined; canRequest: boolean; resolved: boolean };

export function ApprovalsPanel({ caseId, me, canRequest, resolved }: Props) {
  const q = useApprovals(caseId);
  return (
    <Panel title="Approvals">
      <p className="text-sm text-fg-muted">
        A second person approves or rejects each action. Approval is recorded separately from execution, and no refund is ever
        sent to PayPal from here.
      </p>
      {canRequest && <RequestForm caseId={caseId} resolved={resolved} />}
      {q.isPending && <Skeleton className="mt-3 h-20" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && q.data.length === 0 && <p className="mt-3 text-sm text-fg-subtle">No approval requests yet.</p>}
      {q.data && q.data.length > 0 && (
        <ul className="mt-4 space-y-3">
          {q.data.map((a) => (
            <Request key={a.id} caseId={caseId} a={a} me={me} />
          ))}
        </ul>
      )}
    </Panel>
  );
}

function RequestForm({ caseId, resolved }: { caseId: string; resolved: boolean }) {
  const create = useCreateApproval(caseId);
  const packets = usePackets(caseId);
  const toast = useToast();
  const [action, setAction] = useState<ApprovalActionType>("MANUAL_REVIEW");
  const [packetId, setPacketId] = useState("");
  const [why, setWhy] = useState("");
  const actions = (Object.keys(APPROVAL_ACTION) as ApprovalActionType[]).filter(
    (k) => !resolved || k === "EVIDENCE_PACKET_INTERNAL",
  );
  const needsPacket = action === "EVIDENCE_PACKET_INTERNAL";
  const selectedAction = actions.includes(action) ? action : actions[0];

  return (
    <form
      className="mt-3 space-y-3 border-t border-line pt-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!selectedAction) return;
        create.mutate(
          { action_type: selectedAction, justification: why.trim(), ...(needsPacket && packetId ? { packet_id: packetId } : {}) },
          {
            onSuccess: () => {
              setWhy("");
              toast.notify({ tone: "positive", title: "Approval requested", body: "Another reviewer must decide it." });
            },
            onError: (err) => toast.notify({ tone: "critical", title: "Request not created", body: err.message }),
          },
        );
      }}
    >
      <fieldset>
        <legend className="text-sm font-medium">Request approval for</legend>
        <div className="mt-2 space-y-2">
          {actions.map((k) => (
            <label key={k} className="flex cursor-pointer items-start gap-2.5 rounded-md border border-line px-3 py-2 has-[:checked]:border-accent">
              <input type="radio" name="approval-action" value={k} checked={selectedAction === k} onChange={() => setAction(k)} className="mt-1 accent-[var(--color-accent)]" />
              <span>
                <span className="block text-sm">{APPROVAL_ACTION[k].label}</span>
                <span className="block text-xs text-fg-subtle">{APPROVAL_ACTION[k].help}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      {needsPacket && (
        <div>
          <label htmlFor="approval-packet" className="text-sm font-medium">Packet</label>
          <select id="approval-packet" required value={packetId} onChange={(e) => setPacketId(e.target.value)} className={`mt-1 ${INPUT}`}>
            <option value="">{packets.data?.length ? "Choose a packet" : "Generate a packet first"}</option>
            {packets.data?.map((p) => (
              <option key={p.id} value={p.id}>{formatDateTime(p.created_at)} · {p.sha256.slice(0, 8)}</option>
            ))}
          </select>
        </div>
      )}
      <div>
        <label htmlFor="approval-why" className="text-sm font-medium">Justification</label>
        <textarea id="approval-why" required minLength={3} maxLength={2000} rows={2} value={why} onChange={(e) => setWhy(e.target.value)} className={`mt-1 ${INPUT}`} />
      </div>
      <Button type="submit" variant="secondary" busy={create.isPending} disabled={why.trim().length < 3 || (needsPacket && !packetId)}>
        Request approval
      </Button>
    </form>
  );
}

function Request({ caseId, a, me }: { caseId: string; a: ApprovalRequest; me: Me | null | undefined }) {
  const decide = useDecideApproval(caseId);
  const toast = useToast();
  const [comment, setComment] = useState("");
  const snap = a.action_snapshot as Record<string, unknown>;
  const mine = a.requested_by?.id === me?.id;
  const roleOk = me ? a.required_roles.includes(me.role) : false;
  const canDecide = a.status === "PENDING" && roleOk && !mine;
  const commentId = `decide-${a.id}`;

  const act = (verb: "approve" | "reject") =>
    decide.mutate(
      { id: a.id, verb, comment: comment.trim() },
      {
        onSuccess: () => toast.notify({ tone: "positive", title: verb === "approve" ? "Approved" : "Rejected", body: "Your decision is recorded." }),
        onError: (e) => toast.notify({ tone: "critical", title: "Decision not recorded", body: e.message }),
      },
    );

  return (
    <li className="rounded-md border border-line p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{APPROVAL_ACTION[a.action_type].label}</span>
        <Badge tone={APPROVAL_STATUS[a.status].tone}>{APPROVAL_STATUS[a.status].label}</Badge>
      </div>
      {a.action_type === "PREPARE_REFUND" && typeof snap["amount_minor"] === "number" && (
        <p className="tabular mt-1">
          Full refund of {formatMoney(snap["amount_minor"], String(snap["currency"]))} <span className="text-fg-subtle">(intent only)</span>
        </p>
      )}
      {typeof snap["paypal_executable_reason"] === "string" && <p className="mt-0.5 text-xs text-fg-subtle">{snap["paypal_executable_reason"]}</p>}
      <p className="mt-1 break-words text-fg-muted">{a.justification}</p>
      <p className="mt-1 text-xs text-fg-subtle">
        Requested by {a.requested_by?.email ?? "unknown"} · {formatDateTime(a.created_at)} · needs {a.required_roles.join(" or ").toLowerCase()} ·
        snapshot <span className="font-mono">{a.snapshot_sha256.slice(0, 10)}</span>
      </p>

      {a.decision && (
        <div className="mt-2 border-t border-line pt-2 text-xs">
          <p>
            {a.decision.decision === "APPROVED" ? "Approved" : "Rejected"} by {a.decision.decided_by?.email ?? "unknown"} (
            {a.decision.decided_by_role.toLowerCase()}) · {formatDateTime(a.decision.created_at)}
          </p>
          <p className="mt-0.5 break-words text-fg-muted">{a.decision.comment}</p>
        </div>
      )}
      {a.execution && (
        <p className="mt-2 rounded-sm bg-sunken px-2 py-1 text-xs text-fg-muted">
          <span className="font-medium text-fg">{a.execution.status === "NOT_EXECUTED" ? "Not executed" : "Recorded"}:</span>{" "}
          {String(a.execution.detail["effect"] ?? "")} {a.execution.provider_called ? "" : "No payment provider was called."}
        </p>
      )}

      {a.status === "PENDING" && !canDecide && (
        <p className="mt-2 text-xs text-fg-subtle">
          {mine ? "Waiting for another reviewer. You cannot decide your own request." : `Waiting for a ${a.required_roles.join(" or ").toLowerCase()} to decide.`}
        </p>
      )}
      {canDecide && (
        <div className="mt-3 space-y-2 border-t border-line pt-3">
          <label htmlFor={commentId} className="text-sm font-medium">Decision note</label>
          <textarea id={commentId} rows={2} maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)} className={INPUT} />
          <div className="flex gap-2">
            <Button busy={decide.isPending && decide.variables?.verb === "approve"} disabled={comment.trim().length < 3 || decide.isPending} onClick={() => act("approve")}>
              Approve
            </Button>
            <Button variant="secondary" busy={decide.isPending && decide.variables?.verb === "reject"} disabled={comment.trim().length < 3 || decide.isPending} onClick={() => act("reject")}>
              Reject
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}
