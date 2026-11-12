import { clsx } from "clsx";
import { ArrowUpRight, LogOut } from "lucide-react";
import { useRef } from "react";
import { NavLink, Navigate, Outlet, useLocation, Link } from "react-router-dom";
import { AppNavigation } from "./AppNavigation";
import { ErrorState } from "@/components/ui/States";
import { Skeleton } from "@/components/ui/States";
import { useLogout, useMe } from "@/features/auth/session";
import { usePayPalStatus } from "@/features/settings/usePayPalStatus";
import { supports, type Capability } from "@/lib/capabilities";
import { STATIC_DEMO } from "@/lib/staticDemo";
import { StaticDemoBanner } from "@/features/demo/StaticDemoBanner";
import { WorkspaceFonts } from "./WorkspaceFonts";
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
      </header>
      {STATIC_DEMO && <StaticDemoBanner />}
      <AccountBar
        email={me.data.email}
        role={me.data.role}
        merchant={me.data.merchant.name}
      />
      <main
        id="main"
        tabIndex={-1}
        className="workspace-main"
        data-workspace-route={location.pathname}
      >
        <Outlet />
      </main>
      <footer className="workspace-footer">
        <span>SENTINEL / FOLLOW THE MONEY</span>
        <span>Decision support. Human judgment.</span>
      </footer>
    </div>
  );
}
function AccountBar({
  email,
  role,
  merchant,
}: {
  email: string;
  role: string;
  merchant: string;
}) {
  const logout = useLogout(),
    status = usePayPalStatus(),
    mode = status.data?.mode,
    healthy = status.data?.token_check === "ok";
  return (
    <section className="workspace-account-bar" aria-label="Workspace account">
      <div className="workspace-merchant">
        <span>{merchant}</span>
        {mode && (
          <span
            className={clsx(
              "workspace-gateway",
              mode === "fixture"
                ? "text-warning"
                : healthy
                  ? "text-positive"
                  : "text-critical",
            )}
          >
            {mode === "fixture"
              ? "Simulated gateway"
              : healthy
                ? "PayPal sandbox connected"
                : "PayPal sandbox unavailable"}
          </span>
        )}
      </div>
      {logout.isError && (
        <p role="alert" className="text-critical text-sm">
          Sign out failed. Your session may still be active. Please retry sign
          out.
        </p>
      )}
      <div className="workspace-account">
        <span>
          {email} <small>{role}</small>
        </span>
        {!STATIC_DEMO && (
          <button
            aria-label={logout.isError ? "Retry sign out" : "Sign out"}
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            <LogOut size={17} />
          </button>
        )}
      </div>
    </section>
  );
}
