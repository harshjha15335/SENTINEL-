import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { formatScore, RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { useMe } from "@/features/auth/session";
import { isOperator, type PolicyDecision, type RiskAssessment } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

import { Contributions } from "./Contributions";
import { useAssessment, useRescore } from "./useRisk";

const DECISION: Record<PolicyDecision, string> = {
  ALLOW: "would allow without review",
  REVIEW: "would suggest an optional review",
  ESCALATE: "would send to the review queue",
};

type Props = { transactionId: string; scorable: boolean; className?: string; caseSlot?: React.ReactNode };

export function RiskPanel({ transactionId, scorable, className, caseSlot }: Props) {
  const q = useAssessment(transactionId);
  const me = useMe();
  const rescore = useRescore(transactionId);
  const toast = useToast();
  const canScore = isOperator(me.data?.role) && scorable;

  const run = () =>
    rescore.mutate(undefined, {
      onSuccess: (a) => toast.notify({ tone: "positive", title: "Payment scored", body: `${a.risk_band.toLowerCase()} risk, ${formatScore(a.risk_score)}` }),
      onError: (e) => toast.notify({ tone: "critical", title: "Scoring failed", body: e.message }),
    });

  return (
    <Panel
      title="Risk assessment"
      className={className}
      actions={
        canScore && q.data ? (
          <Button variant="ghost" className="h-8 px-2.5 text-xs" busy={rescore.isPending} onClick={run}>
            Re-score
          </Button>
        ) : undefined
      }
    >
      {q.isPending && <Skeleton className="h-40" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data === null && (
        <div>
          <Badge>Not scored</Badge>
          <p className="mt-3 text-sm text-fg-muted">
            {scorable
              ? "No assessment has been recorded for this payment yet."
              : "Only payments with a capture attempt can be scored. SENTINEL shows no score rather than a placeholder number."}
          </p>
          {canScore && (
            <Button className="mt-3" variant="secondary" busy={rescore.isPending} onClick={run}>
              Score this payment
            </Button>
          )}
        </div>
      )}
      {q.data && <Assessment a={q.data} />}
      {caseSlot}
    </Panel>
  );
}

function Assessment({ a }: { a: RiskAssessment }) {
  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge band={a.risk_band} />
          <Badge tone="accent">Model-generated</Badge>
        </div>
        <p className="tabular mt-2 text-3xl font-semibold">{formatScore(a.risk_score)}</p>
        <p className="text-xs text-fg-subtle">
          Calibrated model score. Bands: medium from {formatScore(a.thresholds["medium"] ?? 0)}, high from{" "}
          {formatScore(a.thresholds["high"] ?? 0)}.
        </p>
      </div>
      <p className="rounded-md border border-line bg-sunken px-3 py-2 text-sm text-fg-muted">
        <span className="font-medium text-fg">Shadow policy:</span> {DECISION[a.policy_decision]}. SENTINEL records this
        decision only; it never blocks, captures or reverses a payment.
      </p>
      <Contributions assessment={a} />
      <details className="group text-sm">
        <summary className="cursor-pointer text-fg-muted hover:text-fg">Limitations ({a.limitations.length})</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-fg-muted">
          {a.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </details>
      <p className="text-xs text-fg-subtle">
        <Link to="/model" className="text-accent underline underline-offset-2">{a.model_version}</Link> · {a.feature_version} · scored{" "}
        {formatDateTime(a.created_at)} ({a.trigger.replace("_", " ")})
      </p>
    </div>
  );
}
