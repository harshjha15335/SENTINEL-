import { Download, FileDown } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { downloadUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

import { formatBytes } from "./labels";
import { useGeneratePacket, usePackets } from "./useWorkbench";

export function PacketPanel({ caseId, canGenerate }: { caseId: string; canGenerate: boolean }) {
  const q = usePackets(caseId);
  const generate = useGeneratePacket(caseId);
  const toast = useToast();
  return (
    <Panel title="Evidence packet">
      <p className="text-sm text-fg-muted">
        A PDF of the case, payment provenance, chronology, risk, evidence inventory, findings and review status. Generating it
        does not submit anything to PayPal.
      </p>
      {canGenerate && (
        <Button
          className="mt-3"
          variant="secondary"
          busy={generate.isPending}
          onClick={() =>
            generate.mutate(undefined, {
              onSuccess: () => toast.notify({ tone: "positive", title: "Packet generated", body: "Download it from the list below." }),
              onError: (e) => toast.notify({ tone: "critical", title: "Packet not generated", body: e.message }),
            })
          }
        >
          <FileDown aria-hidden className="size-4" /> Generate packet
        </Button>
      )}
      {q.isPending && <Skeleton className="mt-3 h-12" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && q.data.length === 0 && <p className="mt-3 text-sm text-fg-subtle">No packets generated yet.</p>}
      {q.data && q.data.length > 0 && (
        <ul className="mt-3 space-y-2">
          {q.data.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="min-w-0">
                <span className="tabular block">{formatDateTime(p.created_at)}</span>
                <span className="tabular block text-xs text-fg-subtle">
                  {p.page_count} p. · {formatBytes(p.size_bytes)} · {p.generated_by?.email ?? "unknown"}
                </span>
              </span>
              <a
                href={downloadUrl(`/cases/${caseId}/packets/${p.id}/download`)}
                className="inline-flex shrink-0 items-center gap-1 text-accent hover:underline"
                aria-label={`Download packet generated ${formatDateTime(p.created_at)}`}
              >
                <Download aria-hidden className="size-3.5" /> PDF
              </a>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
