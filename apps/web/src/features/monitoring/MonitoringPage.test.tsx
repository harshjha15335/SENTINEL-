import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { mockApi, renderWithProviders } from "@/test/utils";

import { MonitoringPage } from "./MonitoringPage";

const data = {
  observed_at: "2026-11-06T00:00:00Z", data_origin: "SYNTHETIC_DEMO",
  current_window: { start: "2026-08-08T00:00:00Z", end: "2026-11-06T00:00:00Z" },
  reference_window: { start: "2026-05-10T00:00:00Z", end: "2026-08-08T00:00:00Z" },
  current_transactions: 0, current_scored: 0, high_flag_rate: null, capacity_utilization: null,
  open_cases: 0, overdue_cases: 0, oldest_pending_hours: null, resolution_rate: null,
  resolved_in_window: 0, confirmed_adverse_cases: 0, transaction_volume: [], risk_bands: {},
  model_versions: {}, score_distribution: [], score_psi: null, psi_note: "Insufficient samples.",
  calibration_status: "Unavailable: no validated delayed-label cohort.", case_growth: [],
  feature_comparison: [], limitations: ["Single origin only."], sample_limit: 10000, truncated: false,
};

it("shows absence of data without inventing calibration or drift", async () => {
  mockApi([{ path: /\/monitoring\/risk\?/, body: data }]);
  renderWithProviders(<MonitoringPage />);
  expect(await screen.findByText("No scored payments in this window")).toBeInTheDocument();
  expect(screen.getByText("No transactions in this window")).toBeInTheDocument();
  expect(screen.getByText(/Calibration: Unavailable/)).toBeInTheDocument();
  expect(screen.getByText("Insufficient samples.")).toBeInTheDocument();
});

it("requests a separate origin when the filter changes", async () => {
  const calls = mockApi([{ path: /\/monitoring\/risk\?/, body: data }]);
  renderWithProviders(<MonitoringPage />);
  await screen.findByText("No scored payments in this window");
  await userEvent.selectOptions(screen.getByLabelText("Data origin"), "LIVE_SANDBOX");
  await screen.findByText("No scored payments in this window");
  expect(calls.some(c => c.url.includes("data_origin=LIVE_SANDBOX"))).toBe(true);
});

it("shows real request failures without success metrics", async () => {
  mockApi([{ path: /\/monitoring\/risk\?/, status: 503, body: { error: { message: "Monitoring unavailable" } } }]);
  renderWithProviders(<MonitoringPage />);
  expect(await screen.findByText("Monitoring unavailable")).toBeInTheDocument();
  expect(screen.queryByText("Current window", { exact: true })).not.toBeInTheDocument();
});
