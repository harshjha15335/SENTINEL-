import { clsx } from "clsx";
import { Activity, Gauge, LayoutDashboard, ListChecks, LogOut, Settings, ShieldCheck, ShoppingBag } from "lucide-react";
import { NavLink, Navigate, Outlet, useLocation } from "react-router-dom";

import { Skeleton } from "@/components/ui/States";
import { useLogout, useMe } from "@/features/auth/session";
import { usePayPalStatus } from "@/features/settings/usePayPalStatus";

const NAV = [
  { to: "/", label: "Command Center", icon: LayoutDashboard, end: true },
  { to: "/transactions", label: "Transactions", icon: Activity, end: false },
  { to: "/cases", label: "Review Queue", icon: ListChecks, end: false },
  { to: "/model", label: "Risk Model", icon: Gauge, end: false },
  { to: "/checkout", label: "Sandbox Checkout", icon: ShoppingBag, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

export function AppShell() {
  const me = useMe();
  const location = useLocation();

  if (me.isPending) {
    return (
      <div className="p-6">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }
  if (!me.data) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-raised focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="border-b border-line bg-surface md:sticky md:top-0 md:h-dvh md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="flex h-14 items-center gap-2.5 px-4">
          <ShieldCheck aria-hidden className="size-5 text-accent" />
          <span className="text-sm font-semibold tracking-[0.16em]">SENTINEL</span>
        </div>
        <nav aria-label="Primary" className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex h-9 shrink-0 items-center gap-2.5 rounded-md px-3 text-sm whitespace-nowrap transition-colors",
                  isActive ? "bg-accent-soft text-fg" : "text-fg-muted hover:bg-raised hover:text-fg",
                )
              }
            >
              <Icon aria-hidden className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar email={me.data.email} role={me.data.role} merchant={me.data.merchant.name} />
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function TopBar({ email, role, merchant }: { email: string; role: string; merchant: string }) {
  const logout = useLogout();
  const status = usePayPalStatus();
  const mode = status.data?.mode;
  const healthy = status.data?.token_check === "ok";
  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-line px-4 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <p className="truncate text-sm text-fg-muted">{merchant}</p>
        {mode && (
          <span
            className={clsx(
              "inline-flex h-6 shrink-0 items-center gap-1.5 rounded-sm border px-2 text-[11px] font-medium tracking-wide whitespace-nowrap uppercase",
              mode === "fixture" ? "border-warning/40 text-warning" : healthy ? "border-positive/40 text-positive" : "border-critical/40 text-critical",
            )}
          >
            <span aria-hidden className="size-1.5 rounded-full bg-current" />
            <span className="sm:hidden">{mode === "fixture" ? "Simulated" : healthy ? "Sandbox" : "Offline"}</span>
            <span className="hidden sm:inline">{mode === "fixture" ? "Simulated gateway" : healthy ? "PayPal sandbox connected" : "PayPal sandbox unavailable"}</span>
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm leading-tight">{email}</p>
          <p className="text-[11px] tracking-wide text-fg-subtle uppercase">{role}</p>
        </div>
        <button
          onClick={() => logout.mutate()}
          className="inline-flex size-9 items-center justify-center rounded-md text-fg-muted hover:bg-raised hover:text-fg"
          aria-label="Sign out"
        >
          <LogOut className="size-4" />
        </button>
      </div>
    </header>
  );
}
