import * as Tooltip from "@radix-ui/react-tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import { ToastProvider } from "@/components/ui/Toast";

type Route = { method?: string; path: string | RegExp; status?: number; body: unknown };

/** Route-matching fetch stub. Records calls so tests can assert what the UI sent. */
export function mockApi(routes: Route[]) {
  const calls: { method: string; url: string; body: unknown; headers: Record<string, string> }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({
      method,
      url,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
      headers: (init?.headers ?? {}) as Record<string, string>,
    });
    const route = routes.find(
      (r) => (r.method ?? "GET") === method && (typeof r.path === "string" ? url.endsWith(r.path) : r.path.test(url)),
    );
    if (!route) return new Response(JSON.stringify({ error: { code: "not_found", message: `No mock for ${method} ${url}` } }), { status: 404 });
    return new Response(JSON.stringify(route.body), { status: route.status ?? 200, headers: { "content-type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Tooltip.Provider>
        <ToastProvider>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </ToastProvider>
      </Tooltip.Provider>
    </QueryClientProvider>,
  );
}

export const ME = {
  id: "u1",
  email: "analyst@northwind.example",
  role: "ANALYST",
  merchant: { id: "m1", name: "Northwind Supply Co. (sandbox)", environment: "SANDBOX" },
};

export function txn(overrides: Record<string, unknown> = {}) {
  return {
    id: "t1",
    paypal_order_id: "SIM-ORDER-ABC",
    paypal_capture_id: "SIM-CAPTURE-XYZ",
    amount_minor: 3800,
    currency: "USD",
    quantity: 2,
    status: "CAPTURED",
    provider_status: "COMPLETED",
    payer_reference: "SIM-PAYER",
    data_origin: "SIMULATED",
    product_name: "API Starter Plan",
    failure_reason: null,
    occurred_at: "2026-10-10T12:00:00Z",
    created_at: "2026-10-10T12:00:00Z",
    updated_at: "2026-10-10T12:00:00Z",
    ...overrides,
  };
}
