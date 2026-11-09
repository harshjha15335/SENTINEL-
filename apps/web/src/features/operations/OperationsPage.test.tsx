import { screen } from "@testing-library/react";

import { ME, mockApi, renderWithProviders } from "@/test/utils";

import { OperationsPage } from "./OperationsPage";

const snapshot = {
  observed_at: "2026-10-22T12:00:00Z", ready: false, checks: { schema: "ok" },
  workers: [{ name: "supabase_bridge", status: "HEALTHY", fresh: false, heartbeat_at: "2026-10-22T10:00:00Z", last_success_at: null, processed: 0, failures: 1, last_error: "ConnectError" }],
  inbox_scope: "not_authorized", inbox_fresh: false, inbox: null,
  events: [], scoring_jobs: [{ data_origin: "SIMULATED", status: "DEAD", count: 1 }], investigations: [], exhausted_events: 0,
  integrations: { paypal_mode: "fixture", paypal_credentials_configured: true, last_verified_event_at: null, ai_provider: "none", ai_configured: false, last_completed_ai_run_at: null, verification_note: "Configuration is not provider verification." },
  storage: { backend: "database", database_query: "ok", stored_files: 2, stored_bytes: 42, durability: "Hosted backup policy unverified." },
};

it("restricts non-administrators without fetching operations data", async () => {
  const calls = mockApi([{ path: "/me", body: ME }]);
  renderWithProviders(<OperationsPage />);
  expect(await screen.findByText("Administrator access required.")).toBeInTheDocument();
  expect(calls.some(c => c.url.endsWith("/operations/webhooks"))).toBe(false);
});

it("shows stale workers, stage provenance and unverified integrations", async () => {
  mockApi([{ path: "/me", body: { ...ME, role: "ADMIN" } }, { path: "/operations/webhooks", body: snapshot }]);
  renderWithProviders(<OperationsPage />);
  expect(await screen.findByText("Stale")).toBeInTheDocument();
  expect(screen.getByText("Not ready")).toBeInTheDocument();
  expect(screen.getByText("Dead: 1")).toBeInTheDocument();
  expect(screen.getByText("No verified merchant event recorded")).toBeInTheDocument();
  expect(screen.getByText(/Global inbox totals are restricted/)).toBeInTheDocument();
  expect(screen.getByText("Simulated")).toBeInTheDocument();
});

it("reports unavailable metrics without a success badge", async () => {
  mockApi([{ path: "/me", body: { ...ME, role: "ADMIN" } }, { path: "/operations/webhooks", status: 503, body: { error: { message: "Database unavailable" } } }]);
  renderWithProviders(<OperationsPage />);
  expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
  expect(screen.queryByText("Ready")).not.toBeInTheDocument();
});
