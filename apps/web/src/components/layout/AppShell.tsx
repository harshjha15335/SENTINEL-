import { clsx } from "clsx";
import { ArrowUpRight, LogOut, UserRound, Settings2 } from "lucide-react";
import { useRef } from "react";
import { NavLink, Navigate, Outlet, useLocation, Link } from "react-router-dom";
import { AppNavigation } from "./AppNavigation";
import { ErrorState } from "@/components/ui/States";
import { Skeleton } from "@/components/ui/States";
import { useLogout, useMe } from "@/features/auth/session";
import { supports, type Capability } from "@/lib/capabilities";
import { STATIC_DEMO } from "@/lib/staticDemo";
import { StaticDemoBanner } from "@/features/demo/StaticDemoBanner";
import { WorkspaceFonts } from "./WorkspaceFonts";
import { WorkspaceMotion } from "./WorkspaceMotion";
const PRIMARY: [string, string, Capability][] = [
  ["/app", "Command Center", "dashboard"],
  ["/app/transactions", "Transactions", "transactions"],
  ["/app/cases", "Investigations", "cases"],
  ["/app/model", "Risk Intelligence", "model"],
  ["/app/policy", "Policy Lab", "policy"],
  ["/app/monitoring", "Monitoring", "monitoring"],
];
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
  const nav = (items: [string, string, Capability][]) =>
    items
      .filter(([, , capability]) => supports(capability))
      .map(([to, label]) => (
        <NavLink
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
          {label}
        </NavLink>
      ));
  return (
    <div className="sentinel-workspace">
      <AppNavigation />
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
        <UserAccountMenu email={me.data.email} role={me.data.role} />
      </header>
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
  const userMenu = useRef<HTMLDetailsElement>(null);
  return (
    <details className="workspace-user-menu" ref={userMenu}>
      <summary aria-label="Open account menu" title="Your account">
        <UserRound size={20} aria-hidden="true" />
        <span className="sr-only">Account</span>
      </summary>
      <div className="workspace-user-panel">
        <p className="workspace-user-label">SIGNED IN AS</p>
        <strong className="workspace-user-email">{email}</strong>
        <span className="workspace-user-role">{role}</span>
        <hr />
        <Link to="/app/settings" onClick={() => { if (userMenu.current) userMenu.current.open = false; }}>
          <Settings2 size={16} aria-hidden="true" /> Account &amp; integrations
        </Link>
        {!STATIC_DEMO && (
          <button type="button" onClick={() => logout.mutate()} disabled={logout.isPending}>
            <LogOut size={16} aria-hidden="true" />
            {logout.isPending ? "Signing out…" : "Sign out"}
          </button>
        )}
        {logout.isError && (
          <p role="alert" className="workspace-user-error">Sign out failed. Please retry.</p>
        )}
      </div>
    </details>
  );
}
