import { clsx } from "clsx";
import { ArrowUpRight, LogOut, UserRound, Settings2, LayoutDashboard, ArrowLeftRight, SearchCheck, BarChart3, SlidersHorizontal, Activity, type LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Navigate, Outlet, useLocation, useNavigate, Link } from "react-router-dom";
import { AppNavigation } from "./AppNavigation";
import { ErrorState } from "@/components/ui/States";
import { Skeleton } from "@/components/ui/States";
import { useLogout, useMe } from "@/features/auth/session";
import { supports, type Capability } from "@/lib/capabilities";
import { STATIC_DEMO } from "@/lib/staticDemo";
import { StaticDemoBanner } from "@/features/demo/StaticDemoBanner";
import { WorkspaceFonts } from "./WorkspaceFonts";
import { WorkspaceMotion } from "./WorkspaceMotion";
import { CursorSmudge } from "@/components/ui/CursorSmudge";
const PRIMARY: [string, string, Capability][] = [
  ["/app", "Command Center", "dashboard"],
  ["/app/transactions", "Transactions", "transactions"],
  ["/app/cases", "Investigations", "cases"],
  ["/app/model", "Risk Intelligence", "model"],
  ["/app/policy", "Policy Lab", "policy"],
  ["/app/monitoring", "Monitoring", "monitoring"],
];
const NAV_ICONS: Record<string, LucideIcon> = {
  "/app": LayoutDashboard,
  "/app/transactions": ArrowLeftRight,
  "/app/cases": SearchCheck,
  "/app/model": BarChart3,
  "/app/policy": SlidersHorizontal,
  "/app/monitoring": Activity,
};
const MORE: [string, string, Capability][] = [
  ["/app/network", "Relationship explorer", "network"],
  ["/app/refunds", "Refund review", "refunds"],
  ["/app/disputes", "Dispute preparation", "disputes"],
  ["/app/checkout", "Sandbox checkout", "checkout"],
  ["/app/settings", "Integration & account", "settings"],
  ["/app/demo", "Demo guide", "demo"],
  ["/app/operations", "Operations", "operations"],
];
export function AppShell() {
  return (
    <>
      <WorkspaceFonts />
      <WorkspaceSession />
    </>
  );
}
function WorkspaceSession() {
  const me = useMe(),
    location = useLocation(),
    menu = useRef<HTMLDetailsElement>(null);
  if (me.isPending)
    return (
      <div className="workspace-session-loading" role="status">
        <Skeleton className="h-8 w-48" />
        <p>Opening your workspace…</p>
      </div>
    );
  if (me.isError)
    return (
      <div className="workspace-session-loading">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </div>
    );
  if (!me.data)
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search + location.hash }}
      />
    );
  const more = MORE.filter(
    ([to]) =>
      (to != "/app/operations" || me.data?.role === "ADMIN") &&
      (to != "/app/demo" || me.data?.merchant.environment === "DEMO"),
  );
  const pageLabel = [...PRIMARY, ...more]
    .filter(([to]) => location.pathname === to || (to !== "/app" && location.pathname.startsWith(`${to}/`)))
    .sort((a, b) => b[0].length - a[0].length)[0]?.[1] ?? "Workspace";
  const nav = (items: [string, string, Capability][]) =>
    items
      .filter(([, , capability]) => supports(capability))
      .map(([to, label]) => {
        const Icon = NAV_ICONS[to];
        return <NavLink
          key={to}
          to={to ?? "/app"}
          end={to === "/app"}
          onClick={() => {
            if (menu.current) menu.current.open = false;
          }}
          className={({ isActive }) =>
            clsx("workspace-nav-link", isActive && "is-active")
          }
        >
          {Icon && <Icon size={17} aria-hidden="true" />}
          <span>{label}</span>
        </NavLink>;
      });
  return (
    <div className="sentinel-workspace">
      <AppNavigation />
      <CursorSmudge />
      <a
        className="workspace-skip"
        href="#main"
        onClick={(event) => {
          event.preventDefault();
          const main = document.getElementById("main");
          main?.focus({ preventScroll: true });
          main?.scrollIntoView({ block: "start" });
        }}
      >
        Skip to content
      </a>
      <header className="workspace-global-header">
        <Link to={STATIC_DEMO ? "/" : "/intro"} className="workspace-brand">
          <span>S</span>SENTINEL
        </Link>
        <nav aria-label="Primary" className="workspace-primary-nav">
          {nav(PRIMARY)}
        </nav>
        <details className="workspace-menu" ref={menu}>
          <summary>Explore</summary>
          <nav aria-label="All workspaces">
            <div className="workspace-mobile-links">{nav(PRIMARY)}</div>
            {nav(more)}
            <Link to={STATIC_DEMO ? "/" : "/intro"}>
              Replay the wallet story <ArrowUpRight size={14} />
            </Link>
          </nav>
        </details>
      </header>
      <div className="workspace-topbar">
        <div className="workspace-topbar-location">
          <span>FRAUD OPERATIONS / SENTINEL</span>
          <strong>{pageLabel}</strong>
        </div>
        <UserAccountMenu email={me.data.email} role={me.data.role} />
      </div>
      {STATIC_DEMO && <StaticDemoBanner />}
      <main
        id="main"
        tabIndex={-1}
        className="workspace-main"
        data-workspace-route={location.pathname}
      >
        <WorkspaceMotion key={location.pathname}>
          <Outlet />
        </WorkspaceMotion>
      </main>
      <footer className="workspace-footer">
        <span>SENTINEL / FOLLOW THE MONEY</span>
        <span>Decision support. Human judgment.</span>
      </footer>
    </div>
  );
}
function UserAccountMenu({ email, role }: { email: string; role: string }) {
  const logout = useLogout();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !container.current?.contains(event.target))
        setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        container.current?.querySelector<HTMLButtonElement>(".workspace-account-trigger")?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="workspace-user-menu" ref={container}>
      <button
        className="workspace-account-trigger"
        type="button"
        aria-label="Open account menu"
        aria-expanded={open}
        aria-controls="workspace-account-actions"
        onClick={() => setOpen((current) => !current)}
      >
        <UserRound size={20} aria-hidden="true" />
      </button>
      {open && (
        <div className="workspace-user-panel" id="workspace-account-actions" aria-label="Account actions">
          <p className="workspace-user-label">SIGNED IN AS</p>
          <strong className="workspace-user-email">{email}</strong>
          <span className="workspace-user-role">{role}</span>
          <hr />
          <Link to="/app/settings" onClick={() => setOpen(false)}>
            <Settings2 size={16} aria-hidden="true" /> Account &amp; integrations
          </Link>
          {!STATIC_DEMO && (
            <button
              type="button"
              onClick={() =>
                logout.mutate(undefined, {
                  onSuccess: () => {
                    setOpen(false);
                    navigate("/login", { replace: true });
                  },
                })
              }
              disabled={logout.isPending}
            >
              <LogOut size={16} aria-hidden="true" />
              {logout.isPending ? "Signing out…" : "Sign out"}
            </button>
          )}
          {logout.isError && (
            <p role="alert" className="workspace-user-error">
              Sign out failed. Please retry.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
