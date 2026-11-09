import { clsx } from "clsx";
import type { ReactNode } from "react";

type Props = {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
};

export function Panel({
  title,
  actions,
  children,
  className,
  bodyClassName,
}: Props) {
  return (
    <section className={clsx("workspace-section", className)}>
      {(title || actions) && (
        <header className="workspace-section-heading">
          {title && <h2 className="workspace-section-title">{title}</h2>}
          {actions}
        </header>
      )}
      <div className={clsx("workspace-section-body", bodyClassName)}>
        {children}
      </div>
    </section>
  );
}
