import { screen } from "@testing-library/react";

import { mockApi, renderWithProviders, txn } from "@/test/utils";

import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("keeps sandbox and simulated totals separate", async () => {
    mockApi([
      {
        path: "/api/v1/dashboard/summary",
        body: {
          transactions_total: 3,
          by_status: { CAPTURED: 2, CAPTURE_FAILED: 1 },
          captured_by_origin: [
            { data_origin: "LIVE_SANDBOX", currency: "USD", captured_count: 1, captured_amount_minor: 24900 },
            { data_origin: "SIMULATED", currency: "USD", captured_count: 1, captured_amount_minor: 1900 },
          ],
          webhook_events: { PROCESSED: 2 },
          recent: [txn()],
        },
      },
    ]);
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText("$249.00")).toBeInTheDocument();
    expect(screen.getByText("$19.00")).toBeInTheDocument();
    expect(screen.getByLabelText(/Data origin: Live sandbox/)).toBeInTheDocument();
    expect(screen.getByText(/2 processed/)).toBeInTheDocument();
  });

  it("shows an empty state with a next step", async () => {
    mockApi([
      { path: "/api/v1/dashboard/summary", body: { transactions_total: 0, by_status: {}, captured_by_origin: [], webhook_events: {}, recent: [] } },
    ]);
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText("No captured payments yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Run a sandbox checkout" })).toBeInTheDocument();
  });

  it("shows errors with the correlation reference", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ error: { code: "x", message: "Database unavailable" } }), { status: 503, headers: { "x-correlation-id": "abc123def456" } })),
    );
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
    expect(screen.getByText("Reference abc123def456")).toBeInTheDocument();
  });
});
