import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="workspace-page-heading">
      <div className="min-w-0">
        <h1 className="workspace-page-title">{title}</h1>
        {description && (
          <p className="workspace-page-description">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
