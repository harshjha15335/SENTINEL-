import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ME, mockApi, renderWithProviders } from "@/test/utils";

import { DisputesPage } from "./DisputesPage";

const item = {
  id: "d1",
  case_id: "c1",
  transaction_id: "t1",
  provider_dispute_id: null,
  reason: "ITEM_NOT_RECEIVED",
  status: "DEMO_OPEN",
  stage: "DEMO_INQUIRY",
  response_due_at: null,
  data_origin: "SYNTHETIC_DEMO",
};

it("lets viewers inspect labelled disputes without exposing preparation controls", async () => {
  mockApi([
    { path: "/me", body: { ...ME, role: "VIEWER" } },
    { path: "/disputes?limit=25&offset=0", body: [item] },
    {
      path: "/disputes/d1",
      body: {
        dispute: item,
        checklist: [{ key: "invoice", label: "Invoice", provided: false }],
        drafts: [],
        limitations: ["External submission is disabled."],
      },
    },
  ]);
  renderWithProviders(<DisputesPage />);
  await userEvent.click(
    await screen.findByRole("button", { name: /Demonstration dispute/ }),
  );
  expect(
    await screen.findByText("External submission is disabled."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", {
      name: "Open evidence, case packet and independent approval",
    }),
  ).toHaveAttribute("href", "/app/cases/c1");
  expect(
    screen.queryByRole("button", { name: "Prepare deterministic draft" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Read-only sandbox sync" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Demo case ID")).not.toBeInTheDocument();
});

it("shows genuine sync errors rather than silently substituting fixtures", async () => {
  mockApi([
    { path: "/me", body: { ...ME, role: "ADMIN" } },
    { path: "/disputes?limit=25&offset=0", body: [] },
    {
      path: "/disputes/sync",
      method: "POST",
      status: 503,
      body: {
        error: { message: "Read-only dispute synchronization unavailable" },
      },
    },
  ]);
  renderWithProviders(<DisputesPage />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Read-only sandbox sync" }),
  );
  expect(
    await screen.findByText("Read-only dispute synchronization unavailable"),
  ).toBeInTheDocument();
  expect(screen.getByText("No disputes in this workspace")).toBeInTheDocument();
});
