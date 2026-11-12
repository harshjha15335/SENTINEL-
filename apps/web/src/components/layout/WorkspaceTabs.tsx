export function WorkspaceTabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Investigation workspace"
      className="workspace-context-tabs"
    >
      {tabs.map((tab, i) => (
        <button
          key={tab.id}
          id={`workspace-tab-${tab.id}`}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          aria-controls={`workspace-panel-${tab.id}`}
          tabIndex={active === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(e) => {
            const delta =
              e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
            if (!delta && e.key !== "Home" && e.key !== "End") return;
            e.preventDefault();
            const index =
              e.key === "Home"
                ? 0
                : e.key === "End"
                  ? tabs.length - 1
                  : (i + delta + tabs.length) % tabs.length;
            const next = tabs[index];
            if (next) {
              onChange(next.id);
              document.getElementById(`workspace-tab-${next.id}`)?.focus();
            }
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
