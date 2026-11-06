import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { formatDateTime } from "@/lib/format";
import { api, type Schemas } from "@/lib/api";

export function DemoGuidePage() {
  const q = useQuery({ queryKey: ["judge-scenario"], queryFn: () => api<Schemas["JudgeScenarioOut"]>("/demo/scenario") });
  return <>
    <PageHeader title="Explore SENTINEL" description="Explainable payment review, grounded investigation and private evidence, with a human decision at the end." />
    {q.isPending && <Skeleton className="h-48" />}
    {q.isError && <ErrorState error={q.error} />}
    {q.data && <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Your demonstration workspace">
        <OriginBadge origin={q.data.data_origin} />
        <p className="mt-3 text-xs text-fg-muted">Scenario: {q.data.scenario_version} · Created {formatDateTime(q.data.created_at)} · Review due {q.data.due_at ? formatDateTime(q.data.due_at) : "Not set"}</p>
        <p className="mt-3 text-sm text-fg-muted">This isolated workspace contains generated payments and illustrative attachments. Its investigation is a deterministic summary. No payment, provider confirmation, financial recovery or real AI execution is demonstrated here.</p>
        <p className="mt-3 text-sm text-fg-muted">Your viewer account can explore and download material. An independent administrator is required to decide approval requests.</p>
      </Panel>
      <Panel title="Follow one case">
        <ol className="list-decimal space-y-3 pl-5 text-sm">
          <li><Link className="text-accent hover:underline" to={`/transactions/${q.data.transaction_id}`}>Inspect the payment and SHAP explanations</Link></li>
          <li><Link className="text-accent hover:underline" to={`/cases/${q.data.case_id}`}>Open the prepared investigation workbench</Link><p className="mt-1 text-fg-muted">Read the summary, cited records, unverified demo attachment, packet and pending approval.</p></li>
          <li><Link className="text-accent hover:underline" to="/model">Read the synthetic model benchmark and its limitations</Link></li>
          <li><Link className="text-accent hover:underline" to="/cases">Explore the review queue</Link></li>
          <li><Link className="text-accent hover:underline" to="/policy">Compare shadow policy assumptions</Link></li>
          <li><Link className="text-accent hover:underline" to="/monitoring">Inspect origin-specific risk monitoring</Link></li>
          <li><Link className="text-accent hover:underline" to="/network">Explore recorded payer relationships</Link></li>
          <li><Link className="text-accent hover:underline" to="/refunds">Review approval-protected refund preparation</Link><p className="mt-1 text-fg-muted">The judge account cannot request, approve or execute refunds.</p></li>
          <li><Link className="text-accent hover:underline" to="/disputes">Inspect dispute preparation</Link><p className="mt-1 text-fg-muted">External submissions are disabled; examples retain their fixture labels.</p></li>
        </ol>
      </Panel>
    </div>}
  </>;
}
