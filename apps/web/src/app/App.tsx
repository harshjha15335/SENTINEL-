import * as Tooltip from "@radix-ui/react-tooltip";
import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import {
  BrowserRouter,
  HashRouter,
  Route,
  Routes,
  Navigate,
  useLocation,
} from "react-router-dom";

import { CapabilityBoundary } from "@/components/layout/CapabilityBoundary";
import { AppShell } from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui/States";
import { ToastProvider } from "@/components/ui/Toast";
import { meKey } from "@/features/auth/session";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { ApiError } from "@/lib/api";
import { NotFoundPage } from "@/pages/NotFoundPage";

// Heavy screens load on demand: AG Grid (transactions) and the PayPal SDK (checkout).
const TransactionsPage = lazy(() =>
  import("@/features/transactions/TransactionsPage").then((m) => ({
    default: m.TransactionsPage,
  })),
);
const TransactionDetailPage = lazy(() =>
  import("@/features/transactions/TransactionDetailPage").then((m) => ({
    default: m.TransactionDetailPage,
  })),
);
const CasesPage = lazy(() =>
  import("@/features/cases/CasesPage").then((m) => ({ default: m.CasesPage })),
);
const CaseDetailPage = lazy(() =>
  import("@/features/cases/CaseDetailPage").then((m) => ({
    default: m.CaseDetailPage,
  })),
);
const ModelPage = lazy(() =>
  import("@/features/risk/ModelPage").then((m) => ({ default: m.ModelPage })),
);
const CheckoutPage = lazy(() =>
  import("@/features/checkout/CheckoutPage").then((m) => ({
    default: m.CheckoutPage,
  })),
);

// "/" in normal builds; "/SENTINEL-/" when built for GitHub Pages (Vite `base`).
const ROUTER_BASE = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";
// Hosts that serve one page and cannot rewrite paths (an embedded artifact) keep the route in the hash.
const HASH_ROUTES = import.meta.env.VITE_ROUTER === "hash";
const OperationsPage = lazy(() =>
  import("@/features/operations/OperationsPage").then((m) => ({
    default: m.OperationsPage,
  })),
);

const DemoGuidePage = lazy(() =>
  import("@/features/operations/DemoGuidePage").then((m) => ({
    default: m.DemoGuidePage,
  })),
);

const RefundsPage = lazy(() =>
  import("@/features/refunds/RefundsPage").then((m) => ({
    default: m.RefundsPage,
  })),
);
const DisputesPage = lazy(() =>
  import("@/features/disputes/DisputesPage").then((m) => ({
    default: m.DisputesPage,
  })),
);
const PolicyLabPage = lazy(() =>
  import("@/features/policy/PolicyLabPage").then((m) => ({
    default: m.PolicyLabPage,
  })),
);
const MonitoringPage = lazy(() =>
  import("@/features/monitoring/MonitoringPage").then((m) => ({
    default: m.MonitoringPage,
  })),
);
const NetworkPage = lazy(() =>
  import("@/features/network/NetworkPage").then((m) => ({
    default: m.NetworkPage,
  })),
);

const MarketingHome = lazy(() =>
  import("@/features/experience/Experience").then((m) => ({
    default: m.MarketingHome,
  })),
);
const PublicDemoPayment = lazy(() =>
  import("@/features/experience/Experience").then((m) => ({
    default: m.PublicDemoPayment,
  })),
);
const publicFallback = (
  <main className="experience-loading" role="status">
    <div className="workspace-brand">
      <span>S</span>SENTINEL
    </div>
    <p>Opening Follow the Money…</p>
  </main>
);

const fallback = <Skeleton className="h-64" />;

function makeClient(): QueryClient {
  // Any 401 means the session ended: drop cached data and let the shell redirect to sign-in.
  const onError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401)
      client.setQueryData(meKey, null);
  };
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError }),
    mutationCache: new MutationCache({ onError }),
    defaultOptions: {
      queries: {
        retry: (count, error) =>
          !(error instanceof ApiError && error.status < 500) && count < 2,
        refetchOnWindowFocus: false,
      },
    },
  });
  return client;
}

export function App() {
  const [client] = useState(makeClient);
  return (
    <QueryClientProvider client={client}>
      <Tooltip.Provider>
        <ToastProvider>
          {HASH_ROUTES ? (
            <HashRouter>
              <AppRoutes />
            </HashRouter>
          ) : (
            <BrowserRouter basename={ROUTER_BASE}>
              <AppRoutes />
            </BrowserRouter>
          )}
        </ToastProvider>
      </Tooltip.Provider>
    </QueryClientProvider>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Suspense fallback={publicFallback}>
            <MarketingHome />
          </Suspense>
        }
      />
      <Route
        path="/demo-payment"
        element={
          <Suspense fallback={publicFallback}>
            <PublicDemoPayment />
          </Suspense>
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/app" element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route
          path="transactions"
          element={
            <Suspense fallback={fallback}>
              <TransactionsPage />
            </Suspense>
          }
        />
        <Route
          path="transactions/:id"
          element={
            <Suspense fallback={fallback}>
              <TransactionDetailPage />
            </Suspense>
          }
        />
        <Route
          path="cases"
          element={
            <Suspense fallback={fallback}>
              <CasesPage />
            </Suspense>
          }
        />
        <Route
          path="cases/:id"
          element={
            <Suspense fallback={fallback}>
              <CaseDetailPage />
            </Suspense>
          }
        />
        <Route
          path="model"
          element={
            <Suspense fallback={fallback}>
              <ModelPage />
            </Suspense>
          }
        />
        <Route
          path="checkout"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="checkout">
                <CheckoutPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="demo"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="demo">
                <DemoGuidePage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="operations"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="operations">
                <OperationsPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="refunds"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="refunds">
                <RefundsPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="disputes"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="disputes">
                <DisputesPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="policy"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="policy">
                <PolicyLabPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="monitoring"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="monitoring">
                <MonitoringPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="network"
          element={
            <Suspense fallback={fallback}>
              <CapabilityBoundary capability="network">
                <NetworkPage />
              </CapabilityBoundary>
            </Suspense>
          }
        />
        <Route
          path="settings"
          element={
            <CapabilityBoundary capability="settings">
              <SettingsPage />
            </CapabilityBoundary>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
      {[
        "transactions",
        "cases",
        "model",
        "checkout",
        "demo",
        "operations",
        "refunds",
        "disputes",
        "policy",
        "monitoring",
        "network",
        "settings",
      ].map((path) => (
        <Route key={path} path={`/${path}/*`} element={<LegacyRedirect />} />
      ))}
      <Route
        path="*"
        element={
          <main>
            <NotFoundPage />
          </main>
        }
      />
    </Routes>
  );
}

/** Compatibility retains the entire deep link; API routes are not rewritten. */
function LegacyRedirect() {
  const location = useLocation();
  return (
    <Navigate
      to={`/app${location.pathname}${location.search}${location.hash}`}
      replace
      state={location.state}
    />
  );
}
