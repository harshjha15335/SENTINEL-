import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ME, mockApi, renderWithProviders } from "@/test/utils";

import { RefundsPage } from "./RefundsPage";

const request = {
  id: "r1", case_id: "c1", transaction_id: "t1", amount_minor: 1000, currency: "USD",
  data_origin: "SYNTHETIC_DEMO", status: "PENDING_APPROVAL", requested_by_user_id: "u2",
  snapshot_sha256: "a".repeat(64), submission_started: false, provider_refund_id: null,
  provider_status: null, error_category: null, created_at: "2026-11-06T12:00:00Z",
};

it("keeps a viewer read-only and labels synthetic requests", async () => {
  mockApi([{ path: "/me", body: { ...ME, role: "VIEWER" } }, { path: "/refunds", body: [request] }]);
  renderWithProviders(<RefundsPage />);
  expect(await screen.findByText("Synthetic demo")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Approve intent" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Request independent approval" })).not.toBeInTheDocument();
  expect(screen.getByText(/Provider submission not started/)).toBeInTheDocument();
});

it("sends an independent administrator decision with the snapshot digest", async () => {
  const calls = mockApi([
    { path: "/me", body: { ...ME, role: "ADMIN" } },
    { path: "/refunds", body: [request] },
    { method: "POST", path: "/refunds/r1/decision", body: { ...request, status: "APPROVED" } },
  ]);
  renderWithProviders(<RefundsPage />);
  await userEvent.click(await screen.findByRole("button", { name: "Approve intent" }));
  expect(calls.find(c => c.method === "POST")?.body).toEqual({ decision: "APPROVED", snapshot_sha256: request.snapshot_sha256 });
  expect(calls.some(c => c.url.includes("/execute"))).toBe(false);
});

it("shows the empty state rather than fabricated refund activity", async () => {
  mockApi([{ path: "/me", body: { ...ME, role: "VIEWER" } }, { path: "/refunds", body: [] }]);
  renderWithProviders(<RefundsPage />);
  expect(await screen.findByText("No refund requests")).toBeInTheDocument();
});
