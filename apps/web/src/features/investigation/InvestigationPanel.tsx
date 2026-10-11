import { clsx } from "clsx";
import { Bot, FileText, Loader2, RotateCcw, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { ApiError, type InvestigationFindings, type InvestigationRun, type SourceRef } from "@/lib/api";
import { formatDateTime, shortId } from "@/lib/format";

import { ACTION_LABEL, ERROR_HELP, RUN_STATUS, SOURCE_LABEL } from "./labels";
import { isActive, useAIStatus, useInvestigations, useStartInvestigation } from "./useWorkbench";

type Props = { caseId: string; canRun: boolean };

export function InvestigationPanel({ caseId, canRun }: Props) {
  const runs = useInvestigations(caseId);
  const ai = useAIStatus();
  const start = useStartInvestigation(caseId);
  const toast = useToast();
  const [selected, setSelected] = useState<string | null>(null);

  const list = runs.data ?? [];
  const latest = list[0];
  const running = isActive(latest);
  const lastCompleted = list.find((r) => r.status === "COMPLETED");
  const shown = list.find((r) => r.id === selected) ?? lastCompleted;
  const aiReady = ai.data?.configured === true;

  const run = (mode: "auto" | "deterministic") =>
    start.mutate(mode, {
      onError: (e) =>
        toast.notify({
          tone: "critical",
          title: e instanceof ApiError && e.status === 409 ? "Already running" : "Could not start investigation",
          body: e.message,
        }),
    });

  return (
    <Panel
      title="Investigation"
      actions={
        <span className="flex items-center gap-1.5 text-xs text-fg-subtle">
          <Bot aria-hidden className="size-3.5" />
          {ai.isPending ? "Checking AI provider…" : aiReady ? `AI agent: ${ai.data?.provider} · ${ai.data?.model_name}` : "AI provider not configured"}
        </span>
      }
    >
      {canRun && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Button busy={start.isPending} disabled={running} onClick={() => run("auto")}>
            {aiReady ? "Run AI investigation" : "Generate deterministic summary"}
          </Button>
          {aiReady && (
            <Button variant="secondary" disabled={running || start.isPending} onClick={() => run("deterministic")}>
              Deterministic summary only
            </Button>
          )}
          <p className="w-full text-xs text-fg-subtle">
            {aiReady
              ? "The agent reads this case through read-only tools. It cannot refund, contact anyone or change the case."
              : "Without AI credentials SENTINEL summarises the stored records by fixed rules. It is not AI analysis."}
          </p>
        </div>
      )}
      {!canRun && <p className="mb-4 text-sm text-fg-subtle">Your role can read investigations but not start them.</p>}

      {runs.isPending && <Skeleton className="h-40" />}
      {runs.isError && <ErrorState error={runs.error} onRetry={() => void runs.refetch()} />}

      {latest && running && <RunProgress run={latest} />}
      {latest && latest.status === "FAILED" && latest.id !== shown?.id && (
        <FailedRun run={latest} onRetry={canRun ? () => run("auto") : undefined} retrying={start.isPending} />
      )}

      {runs.data && list.length === 0 && (
        <EmptyState title="No investigation yet">
          {canRun ? "Run one to collect verified facts, indicators and missing evidence for this case." : "No one has investigated this case yet."}
        </EmptyState>
      )}

      {shown?.findings && <Findings run={shown} findings={shown.findings} />}

      {list.length > 0 && <History runs={list} shownId={shown?.id} onSelect={setSelected} />}
    </Panel>
  );
}

function RunProgress({ run }: { run: InvestigationRun }) {
  return (
    <div role="status" aria-live="polite" className="mb-4 flex items-center gap-3 rounded-md border border-accent/40 bg-accent-soft px-3 py-2 text-sm">
      <Loader2 aria-hidden className="size-4 animate-spin text-accent" />
      <span>
        {run.status === "QUEUED" ? "Queued" : run.mode === "AI_AGENT" ? "Agent is reading the case records" : "Summarising the case records"}
        <span className="text-fg-muted"> · started {formatDateTime(run.started_at ?? run.created_at)}</span>
      </span>
    </div>
  );
}

function FailedRun({ run, onRetry, retrying }: { run: InvestigationRun; onRetry?: () => void; retrying: boolean }) {
  return (
    <div role="alert" className="mb-4 rounded-md border border-critical/40 bg-critical-soft p-3 text-sm">
      <p className="font-medium">Latest run failed{run.error_category ? `: ${ERROR_HELP[run.error_category]}` : ""}</p>
      {run.error_message && <p className="mt-1 text-xs break-words text-fg-muted">{run.error_message}</p>}
      <p className="mt-1 text-xs text-fg-subtle">Nothing on the case changed. Earlier results are kept.</p>
      {onRetry && (
        <Button variant="secondary" className="mt-2 h-8" busy={retrying} onClick={onRetry}>
          <RotateCcw aria-hidden className="size-3.5" /> Retry
        </Button>
      )}
    </div>
  );
}

function Findings({ run, findings: f }: { run: InvestigationRun; findings: InvestigationFindings }) {
  const ai = run.generated_by_ai;
  return (
    <article aria-label="Investigation findings" className="space-y-4">
      <div className={clsx("rounded-md border px-3 py-2 text-sm", ai ? "border-accent/40 bg-accent-soft" : "border-line-strong bg-sunken")}>
        <p className="flex flex-wrap items-center gap-2 font-medium">
          {ai ? <Bot aria-hidden className="size-4 text-accent" /> : <FileText aria-hidden className="size-4 text-fg-muted" />}
          {run.label}
          <Badge tone={ai ? "accent" : "neutral"}>{ai ? "Model-generated" : "Rule-based"}</Badge>
        </p>
        <p className="mt-0.5 text-xs text-fg-muted">
          {ai
            ? `${run.provider} · ${run.model_name} · prompt ${run.prompt_version}. Every citation below was checked against the records this run read.`
            : "Restates stored records by fixed rules. No language model was used."}{" "}
          Completed {formatDateTime(run.completed_at)}.
        </p>
      </div>

      <p className="text-sm leading-relaxed">{f.summary}</p>

      <div className="rounded-md border border-line p-3">
        <p className="text-xs text-fg-subtle">Recommended next step</p>
        <p className="mt-0.5 font-medium">{ACTION_LABEL[f.recommended_action]}</p>
        <p className="mt-1 text-sm text-fg-muted">{f.recommendation_rationale}</p>
        <p className="mt-2 flex items-center gap-1.5 text-xs text-fg-subtle">
          <ShieldCheck aria-hidden className="size-3.5" /> A person must approve any action. SENTINEL has not acted on this.
        </p>
      </div>

      <Section title={`Verified facts (${f.verified_facts.length})`}>
        <ul className="space-y-2">
          {f.verified_facts.map((x, i) => (
            <li key={i} className="text-sm">
              {x.statement} <Sources refs={x.sources} />
            </li>
          ))}
        </ul>
      </Section>

      <div className="grid gap-4 md:grid-cols-2">
        <Section title={`Risk indicators (${f.risk_indicators.length})`}>
          <Indicators items={f.risk_indicators} empty="None identified." tone="critical" />
        </Section>
        <Section title={`Counter-indicators (${f.counter_indicators.length})`}>
          <Indicators items={f.counter_indicators} empty="None identified." tone="positive" />
        </Section>
      </div>

      {f.evidence_references.length > 0 && (
        <Section title="Evidence referenced">
          <ul className="space-y-2">
            {f.evidence_references.map((r) => (
              <li key={r.evidence_id} className="text-sm">
                <span className="font-mono text-xs text-fg-subtle">{shortId(r.evidence_id)}</span> {r.relevance}
                {r.excerpt && (
                  <blockquote className="mt-1 border-l-2 border-line-strong pl-3 text-fg-muted">“{r.excerpt}”</blockquote>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Section title="Missing information">
          <List items={f.missing_information} empty="Nothing listed." />
        </Section>
        <Section title="Limitations">
          <List items={f.limitations} empty="None stated." />
        </Section>
      </div>

      <ToolTrace run={run} />
    </article>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-xs font-medium tracking-wide text-fg-subtle uppercase">{title}</h3>
      {children}
    </section>
  );
}

function Indicators({ items, empty, tone }: { items: InvestigationFindings["risk_indicators"]; empty: string; tone: "critical" | "positive" }) {
  if (items.length === 0) return <p className="text-sm text-fg-muted">{empty}</p>;
  return (
    <ul className="space-y-2">
      {items.map((x, i) => (
        <li key={i} className={clsx("border-l-2 pl-2.5 text-sm", tone === "critical" ? "border-critical/60" : "border-positive/60")}>
          {x.description} <Sources refs={x.sources} />
        </li>
      ))}
    </ul>
  );
}

function List({ items, empty }: { items: string[]; empty: string }) {
  if (items.length === 0) return <p className="text-sm text-fg-muted">{empty}</p>;
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm text-fg-muted">
      {items.map((x) => (
        <li key={x}>{x}</li>
      ))}
    </ul>
  );
}

function Sources({ refs }: { refs: SourceRef[] }) {
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {refs.map((r) => (
        <span
          key={`${r.kind}:${r.id}`}
          title={`${SOURCE_LABEL[r.kind]} ${r.id}`}
          className="rounded-sm border border-line px-1 font-mono text-[10px] text-fg-subtle"
        >
          {SOURCE_LABEL[r.kind]} {r.id.slice(0, 6)}
        </span>
      ))}
    </span>
  );
}

function ToolTrace({ run }: { run: InvestigationRun }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-fg-muted hover:text-fg">
        Tool calls ({run.tool_calls.length}) · {run.source_refs.length} records read
        {run.duration_ms != null && <span className="tabular"> · {(run.duration_ms / 1000).toFixed(1)} s</span>}
      </summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[420px] text-xs">
          <caption className="sr-only">Tools the investigation called</caption>
          <thead>
            <tr className="text-left text-fg-subtle">
              <th className="py-1 pr-3 font-medium">Tool</th>
              <th className="py-1 pr-3 font-medium">Outcome</th>
              <th className="py-1 pr-3 text-right font-medium">Records</th>
              <th className="py-1 text-right font-medium">ms</th>
            </tr>
          </thead>
          <tbody>
            {run.tool_calls.map((c, i) => (
              <tr key={i} className="border-t border-line">
                <td className="py-1 pr-3 font-mono">{c.name}</td>
                <td className="py-1 pr-3">
                  <Badge tone={c.outcome === "ok" ? "neutral" : c.outcome === "denied" ? "critical" : "warning"}>{c.outcome}</Badge>
                  {c.note && <span className="ml-1.5 text-fg-subtle">{c.note}</span>}
                </td>
                <td className="tabular py-1 pr-3 text-right">{c.records.length}</td>
                <td className="tabular py-1 text-right">{c.duration_ms}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function History({ runs, shownId, onSelect }: { runs: InvestigationRun[]; shownId?: string; onSelect: (id: string) => void }) {
  return (
    <details className="mt-4 text-sm" open={runs.length > 1 && runs[0]?.status === "FAILED"}>
      <summary className="cursor-pointer text-fg-muted hover:text-fg">Run history ({runs.length})</summary>
      <ul className="mt-2 divide-y divide-line rounded-md border border-line">
        {runs.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center gap-2 px-3 py-2">
            <Badge tone={RUN_STATUS[r.status].tone}>{RUN_STATUS[r.status].label}</Badge>
            <span className="text-xs text-fg-muted">{r.generated_by_ai ? "AI agent" : "Deterministic"}</span>
            <span className="tabular text-xs text-fg-subtle">{formatDateTime(r.created_at)}</span>
            {r.initiated_by && <span className="text-xs text-fg-subtle">{r.initiated_by.email}</span>}
            {r.status === "COMPLETED" && (
              <button
                type="button"
                onClick={() => onSelect(r.id)}
                aria-pressed={r.id === shownId}
                className="ml-auto text-xs font-medium text-accent hover:underline aria-pressed:text-fg-muted aria-pressed:no-underline"
              >
                {r.id === shownId ? "Showing" : "Show findings"}
              </button>
            )}
            {r.status === "FAILED" && r.error_category && (
              <span className="ml-auto text-xs text-critical">{r.error_category.toLowerCase().replaceAll("_", " ")}</span>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
