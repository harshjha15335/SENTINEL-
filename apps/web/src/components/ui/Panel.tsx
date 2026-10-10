import { clsx } from "clsx";
import type { ReactNode } from "react";

type Props = { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClassName?: string };

export function Panel({ title, actions, children, className, bodyClassName }: Props) {
  return (
    <section className={clsx("rounded-lg border border-line bg-surface shadow-[var(--shadow-raised)]", className)}>
      {(title || actions) && (
        <header className="flex min-h-11 items-center justify-between gap-3 border-b border-line px-4 py-2">
          {title && <h2 className="text-[13px] font-medium tracking-wide text-fg-muted uppercase">{title}</h2>}
          {actions}
        </header>
      )}
      <div className={clsx("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
