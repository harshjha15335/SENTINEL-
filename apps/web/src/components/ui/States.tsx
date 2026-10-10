import { clsx } from "clsx";
import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={clsx("animate-pulse rounded-sm bg-raised", className)} />;
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-10 text-center">
      <Inbox aria-hidden className="size-5 text-fg-subtle" />
      <p className="text-sm font-medium text-fg">{title}</p>
      {children && <p className="max-w-md text-sm text-fg-muted">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong";
  const cid = error instanceof ApiError ? error.correlationId : null;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md border border-critical/40 bg-critical-soft p-3 text-sm">
      <AlertTriangle aria-hidden className="mt-0.5 size-4 shrink-0 text-critical" />
      <div className="min-w-0 flex-1">
        <p className="text-fg">{message}</p>
        {cid && <p className="mt-1 font-mono text-xs text-fg-subtle">Reference {cid}</p>}
      </div>
      {onRetry && (
        <button onClick={onRetry} className="text-sm font-medium text-accent hover:underline">
          Retry
        </button>
      )}
    </div>
  );
}
