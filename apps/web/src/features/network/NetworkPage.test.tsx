import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { mockApi, renderWithProviders } from "@/test/utils";

import { NetworkPage } from "./NetworkPage";

const data = {
  data_origin: "SYNTHETIC_DEMO", window: { start: "2026-08-08T00:00:00Z", end: "2026-11-06T00:00:00Z" },
  transaction_count: 1, repeated_payer_groups: 0, truncated: true, limit: 12,
  nodes: [
    { id: "merchant", kind: "merchant", label: "Your merchant", record_id: null, risk_band: null, source: "scope" },
    { id: "payer:REF-1", kind: "payer", label: "REF-1", record_id: null, risk_band: null, source: "stored reference" },
    { id: "transaction:t1", kind: "transaction", label: "t1", record_id: "t1", risk_band: "HIGH", source: "transaction" },
  ],
  edges: [
    { source: "merchant", target: "transaction:t1", relationship: "owns", explanation: "Merchant owns this payment.", transaction_id: "t1", data_origin: "SYNTHETIC_DEMO" },
    { source: "payer:REF-1", target: "transaction:t1", relationship: "recorded_payer", explanation: "Recorded reference, not verified identity.", transaction_id: "t1", data_origin: "SYNTHETIC_DEMO" },
  ],
  limitations: ["No invented device, IP or card data."],
};

it("explains graph edges and supports accessible record selection", async () => {
  mockApi([{ path: /\/network\?/, body: data }]);
  renderWithProviders(<NetworkPage />);
  expect(await screen.findByText("Recorded reference, not verified identity.")).toBeInTheDocument();
  expect(screen.getAllByText("Open source payment")).toHaveLength(2);
  await userEvent.click(screen.getByRole("button", { name: "Payer: REF-1" }));
  expect(screen.getByRole("button", { name: "Payer: REF-1" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByText("Open source payment")).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Open record" })).toHaveAttribute("href", "/transactions/t1");
  expect(screen.getByText(/View truncated/)).toBeInTheDocument();
});

it("has an explicit empty network state", async () => {
  mockApi([{ path: /\/network\?/, body: { ...data, transaction_count: 0, nodes: [], edges: [], truncated: false } }]);
  renderWithProviders(<NetworkPage />);
  expect(await screen.findByText("No payments in this origin and window")).toBeInTheDocument();
});
