import * as Tooltip from "@radix-ui/react-tooltip";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

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
const TransactionsPage = lazy(() => import("@/features/transactions/TransactionsPage").then((m) => ({ default: m.TransactionsPage })));
const TransactionDetailPage = lazy(() =>
  import("@/features/transactions/TransactionDetailPage").then((m) => ({ default: m.TransactionDetailPage })),
);
const CheckoutPage = lazy(() => import("@/features/checkout/CheckoutPage").then((m) => ({ default: m.CheckoutPage })));

const fallback = <Skeleton className="h-64" />;

function makeClient(): QueryClient {
  // Any 401 means the session ended: drop cached data and let the shell redirect to sign-in.
  const onError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) client.setQueryData(meKey, null);
  };
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError }),
    mutationCache: new MutationCache({ onError }),
    defaultOptions: {
      queries: {
        retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
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
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </ToastProvider>
      </Tooltip.Provider>
    </QueryClientProvider>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="transactions" element={<Suspense fallback={fallback}><TransactionsPage /></Suspense>} />
        <Route path="transactions/:id" element={<Suspense fallback={fallback}><TransactionDetailPage /></Suspense>} />
        <Route path="checkout" element={<Suspense fallback={fallback}><CheckoutPage /></Suspense>} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
