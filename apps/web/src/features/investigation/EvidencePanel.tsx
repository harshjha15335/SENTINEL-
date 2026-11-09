import { CheckCircle2, CircleDashed, Download, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { OriginBadge } from "@/components/ui/OriginBadge";
import { Panel } from "@/components/ui/Panel";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";
import { useToast } from "@/components/ui/Toast";
import { downloadUrl, type EvidenceCategory, type EvidenceList } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

import { CATEGORY_LABEL, formatBytes, INPUT } from "./labels";
import { useEvidence, useUploadEvidence } from "./useWorkbench";

const EXTENSIONS: Record<string, string[]> = {
  "application/pdf": [".pdf"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
};

export function EvidencePanel({ caseId, canUpload }: { caseId: string; canUpload: boolean }) {
  const q = useEvidence(caseId);
  return (
    <Panel title={`Evidence${q.data ? ` (${q.data.items.length})` : ""}`}>
      {q.isPending && <Skeleton className="h-28" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && (
        <>
          <p className="mb-3 text-xs text-fg-subtle">
            Files the merchant uploaded. Accepting a file does not make it authentic; categories are the uploader's own labels.
          </p>
          {q.data.items.length === 0 ? (
            <EmptyState title="No evidence uploaded">PDF, PNG or JPEG files up to {formatBytes(q.data.max_bytes)}.</EmptyState>
          ) : (
            <ul className="divide-y divide-line rounded-md border border-line">
              {q.data.items.map((e) => (
                <li key={e.id} className="flex flex-col gap-1.5 px-3 py-2.5 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium" title={e.original_filename}>{e.original_filename}</p>
                    <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-fg-muted">
                      <Badge>{CATEGORY_LABEL[e.category]}</Badge>
                      <OriginBadge origin={e.data_origin} />
                      <span className="tabular">{formatBytes(e.size_bytes)}</span>
                      <span>· {e.extraction_status === "EXTRACTED" ? `text read${e.page_count ? `, ${e.page_count} p.` : ""}` : e.extraction_status.toLowerCase().replaceAll("_", " ")}</span>
                    </p>
                    {e.description && <p className="mt-1 text-xs break-words text-fg-muted">{e.description}</p>}
                    <p className="mt-0.5 font-mono text-[11px] text-fg-subtle" title={`SHA-256 ${e.sha256}`}>
                      sha256 {e.sha256.slice(0, 16)}… · {e.uploaded_by?.email ?? "unknown"} · {formatDateTime(e.created_at)}
                    </p>
                  </div>
                  <a
                    href={downloadUrl(`/cases/${caseId}/evidence/${e.id}/download`)}
                    className="inline-flex shrink-0 items-center gap-1 text-sm text-accent hover:underline"
                    aria-label={`Download ${e.original_filename}`}
                  >
                    <Download aria-hidden className="size-3.5" /> Download
                  </a>
                </li>
              ))}
            </ul>
          )}
          {canUpload && <UploadForm caseId={caseId} list={q.data} />}
        </>
      )}
    </Panel>
  );
}

function UploadForm({ caseId, list }: { caseId: string; list: EvidenceList }) {
  const upload = useUploadEvidence(caseId);
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<EvidenceCategory>("INVOICE");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const accept = list.accepted_types.flatMap((t) => [t, ...(EXTENSIONS[t] ?? [])]).join(",");

  const choose = (f: File | null) => {
    setError(null);
    setFile(f);
    if (!f) return;
    const okType = list.accepted_types.includes(f.type) && (EXTENSIONS[f.type] ?? []).some((x) => f.name.toLowerCase().endsWith(x));
    if (!okType) setError("Only PDF, PNG and JPEG files are accepted.");
    else if (f.size > list.max_bytes) setError(`Files may be at most ${formatBytes(list.max_bytes)}.`);
  };

  return (
    <form
      className="mt-4 grid gap-3 border-t border-line pt-4 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!file || error) return;
        upload.mutate(
          { file, category, description: description.trim() },
          {
            onSuccess: () => {
              toast.notify({ tone: "positive", title: "Evidence uploaded", body: "Stored privately and attached to this case." });
              setFile(null);
              setDescription("");
              if (fileRef.current) fileRef.current.value = "";
            },
            onError: (err) => setError(err.message),
          },
        );
      }}
    >
      <div className="sm:col-span-2">
        <label htmlFor="evidence-file" className="text-sm font-medium">Upload evidence</label>
        <input
          ref={fileRef}
          id="evidence-file"
          type="file"
          accept={accept}
          aria-describedby="evidence-file-help"
          aria-invalid={error ? true : undefined}
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm text-fg-muted file:mr-3 file:rounded-md file:border file:border-line-strong file:bg-raised file:px-3 file:py-1.5 file:text-sm file:text-fg"
        />
        <p id="evidence-file-help" className="mt-1 text-xs text-fg-subtle">
          PDF, PNG or JPEG, up to {formatBytes(list.max_bytes)}. PDFs with scripts or passwords are refused.
        </p>
      </div>
      <div>
        <label htmlFor="evidence-category" className="text-sm font-medium">What is it?</label>
        <select id="evidence-category" value={category} onChange={(e) => setCategory(e.target.value as EvidenceCategory)} className={`mt-1 ${INPUT}`}>
          {(Object.keys(CATEGORY_LABEL) as EvidenceCategory[]).map((c) => (
            <option key={c} value={c}>{CATEGORY_LABEL[c]}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="evidence-description" className="text-sm font-medium">Description <span className="text-fg-subtle">(optional)</span></label>
        <input id="evidence-description" maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} className={`mt-1 ${INPUT}`} />
      </div>
      {error && (
        <p role="alert" className="text-sm text-critical sm:col-span-2">{error}</p>
      )}
      <div className="sm:col-span-2">
        <Button type="submit" variant="secondary" busy={upload.isPending} disabled={!file || !!error}>
          <Upload aria-hidden className="size-4" /> Upload
        </Button>
      </div>
    </form>
  );
}

export function ChecklistPanel({ caseId }: { caseId: string }) {
  const q = useEvidence(caseId);
  return (
    <Panel title="Evidence checklist">
      {q.isPending && <Skeleton className="h-24" />}
      {q.isError && <ErrorState error={q.error} onRetry={() => void q.refetch()} />}
      {q.data && (
        <>
          <ul className="space-y-2">
            {q.data.checklist.map((c) => (
              <li key={c.key} className="flex items-start gap-2 text-sm">
                {c.provided ? (
                  <CheckCircle2 aria-hidden className="mt-0.5 size-4 shrink-0 text-positive" />
                ) : (
                  <CircleDashed aria-hidden className="mt-0.5 size-4 shrink-0 text-fg-subtle" />
                )}
                <span>
                  {c.label}
                  <span className="sr-only">{c.provided ? " (provided)" : " (missing)"}</span>
                  {c.provided && <span className="block text-xs text-fg-subtle">Provided by the merchant; not verified</span>}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-fg-subtle">Based on the categories uploaders chose. SENTINEL does not check document contents.</p>
        </>
      )}
    </Panel>
  );
}
