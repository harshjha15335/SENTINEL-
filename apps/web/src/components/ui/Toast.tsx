import { clsx } from "clsx";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type Toast = { id: number; tone: "positive" | "critical"; title: string; body?: string };
type Ctx = { notify: (t: Omit<Toast, "id">) => void };

const ToastContext = createContext<Ctx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((ts) => ts.filter((t) => t.id !== id)), []);
  const notify = useCallback(
    (t: Omit<Toast, "id">) => {
      const id = Date.now() + Math.random();
      setToasts((ts) => [...ts.slice(-2), { ...t, id }]);
      window.setTimeout(() => dismiss(id), 6000);
    },
    [dismiss],
  );
  const value = useMemo(() => ({ notify }), [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="fixed right-4 bottom-4 z-50 flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={clsx(
              "flex items-start gap-3 rounded-md border bg-raised p-3 text-sm shadow-[var(--shadow-overlay)]",
              t.tone === "positive" ? "border-positive/40" : "border-critical/40",
            )}
          >
            {t.tone === "positive" ? (
              <CheckCircle2 aria-hidden className="mt-0.5 size-4 text-positive" />
            ) : (
              <AlertTriangle aria-hidden className="mt-0.5 size-4 text-critical" />
            )}
            <div className="min-w-0 flex-1">
              <p className="font-medium text-fg">{t.title}</p>
              {t.body && <p className="mt-0.5 text-fg-muted">{t.body}</p>}
            </div>
            <button aria-label="Dismiss notification" onClick={() => dismiss(t.id)} className="text-fg-subtle hover:text-fg">
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Ctx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
