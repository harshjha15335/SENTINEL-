import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ME, mockApi, renderWithProviders, txn } from "@/test/utils";

import { CheckoutPage } from "./CheckoutPage";

const PRODUCTS = [
  { id: "p1", sku: "NW-API-STARTER", name: "API Starter Plan", description: "Monthly plan", price_minor: 1900, currency: "USD" },
  { id: "p2", sku: "NW-TEAM", name: "Team Workspace", description: "Annual", price_minor: 24900, currency: "USD" },
];
const FIXTURE_STATUS = {
  mode: "fixture",
  credentials_configured: false,
  token_check: "ok",
  token_error: null,
  client_id: null,
  webhook_id_configured: false,
  data_origin: "SIMULATED",
};

describe("CheckoutPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("runs the simulated flow without sending a price and shows the provenance", async () => {
    const calls = mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/products", body: PRODUCTS },
      { path: "/api/v1/paypal/status", body: FIXTURE_STATUS },
      { method: "POST", path: "/api/v1/paypal/orders", status: 201, body: { transaction_id: "t1", paypal_order_id: "SIM-ORDER-ABC", status: "ORDER_CREATED", data_origin: "SIMULATED" } },
      { method: "POST", path: /\/paypal\/orders\/SIM-ORDER-ABC\/capture$/, body: txn() },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<CheckoutPage />);

    await user.click(await screen.findByRole("button", { name: "Increase quantity" }));
    expect(screen.getByText("$38.00")).toBeInTheDocument();
    expect(screen.getByText("Simulated workflow")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /simulate buyer approval/i }));
    expect(await screen.findByText("Capture confirmed")).toBeInTheDocument();

    const create = calls.find((c) => c.method === "POST" && c.url.endsWith("/paypal/orders"));
    expect(create?.body).toEqual({ product_id: "p1", quantity: 2 });
    expect(create?.headers["Idempotency-Key"]).toMatch(/^web-/);
    expect(screen.getAllByLabelText(/Data origin: Simulated/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Open transaction" })).toHaveAttribute("href", "/transactions/t1");
  });

  it("explains the exact credential dependency in sandbox mode", async () => {
    mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/products", body: PRODUCTS },
      { path: "/api/v1/paypal/status", body: { ...FIXTURE_STATUS, mode: "sandbox", token_check: "not_attempted", data_origin: "LIVE_SANDBOX" } },
    ]);
    renderWithProviders(<CheckoutPage />);
    expect(await screen.findByText("PayPal sandbox credentials required")).toBeInTheDocument();
    expect(screen.getByText("SENTINEL_PAYPAL_CLIENT_ID")).toBeInTheDocument();
  });

  it("keeps viewers read-only", async () => {
    mockApi([
      { path: "/api/v1/me", body: { ...ME, role: "VIEWER" } },
      { path: "/api/v1/products", body: PRODUCTS },
      { path: "/api/v1/paypal/status", body: FIXTURE_STATUS },
    ]);
    renderWithProviders(<CheckoutPage />);
    expect(await screen.findByText(/Your role is read-only/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /simulate/i })).not.toBeInTheDocument();
  });

  it("surfaces provider failures", async () => {
    mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/products", body: PRODUCTS },
      { path: "/api/v1/paypal/status", body: FIXTURE_STATUS },
      { method: "POST", path: "/api/v1/paypal/orders", status: 502, body: { error: { code: "payment_provider_error", message: "PayPal rejected the order", details: {} } } },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<CheckoutPage />);
    await user.click(await screen.findByRole("button", { name: /simulate buyer approval/i }));
    await waitFor(() => expect(screen.getAllByText("PayPal rejected the order").length).toBeGreaterThan(0));
  });
});
