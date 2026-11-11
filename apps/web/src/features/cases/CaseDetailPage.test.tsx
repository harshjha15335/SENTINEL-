import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";

import { ME, mockApi, renderWithProviders, txn } from "@/test/utils";

import { CaseDetailPage } from "./CaseDetailPage";

const baseCase = {
  id: "c1",
  transaction_id: "t1",
  risk_assessment_id: null,
  source: "RISK_MODEL",
  status: "OPEN",
  priority: "HIGH",
  title: "High risk payment needs review",
  assignee: null,
  due_at: "2099-01-01T00:00:00Z",
  resolution: null,
  resolution_note: null,
  resolved_at: null,
  data_origin: "SYNTHETIC_DEMO",
  created_at: "2026-10-10T12:00:00Z",
  updated_at: "2026-10-10T12:00:00Z",
  transaction: txn({ data_origin: "SYNTHETIC_DEMO" }),
  notes: [],
  assessment: null,
  audit: [],
};

describe("CaseDetailPage", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("resolves with a conclusion and reasoning, and says no payment changes", async () => {
    const calls = mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/cases/c1", body: baseCase },
      {
        path: "/api/v1/transactions/t1/risk",
        status: 404,
        body: { error: { code: "not_found", message: "not scored" } },
      },
      {
        method: "POST",
        path: "/api/v1/cases/c1/resolve",
        body: {
          ...baseCase,
          status: "RESOLVED",
          resolution: "LEGITIMATE",
          resolution_note: "Known customer",
          resolved_at: "2026-10-10T13:00:00Z",
        },
      },
    ]);
    renderWithProviders(
      <Routes>
        <Route path="/cases/:id" element={<CaseDetailPage />} />
      </Routes>,
      { route: "/cases/c1" },
    );
    await userEvent.click(
      await screen.findByRole("tab", { name: "Decision & approvals" }),
    );
    const submit = await screen.findByRole("button", { name: "Resolve case" });
    expect(submit).toBeDisabled();
    expect(
      screen.getByText(/does not refund, block or contact anyone/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByLabelText(/Legitimate/));
    await userEvent.type(screen.getByLabelText("Reasoning"), "Known customer");
    await userEvent.click(submit);

    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toEqual({
      resolution: "LEGITIMATE",
      note: "Known customer",
    });
    expect(await screen.findByText("Outcome")).toBeInTheDocument();
  });

  it("preserves an unsent note across workspace tabs and supports keyboard navigation", async () => {
    mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/cases/c1", body: baseCase },
      {
        path: "/api/v1/transactions/t1/risk",
        status: 404,
        body: { error: { code: "not_found", message: "not scored" } },
      },
    ]);
    renderWithProviders(
      <Routes>
        <Route path="/cases/:id" element={<CaseDetailPage />} />
      </Routes>,
      { route: "/cases/c1" },
    );
    await userEvent.click(
      await screen.findByRole("tab", { name: "Notes & activity" }),
    );
    await userEvent.type(
      screen.getByLabelText("Add a note"),
      "Unsent investigation context",
    );
    await userEvent.click(
      screen.getByRole("tab", { name: "Evidence & packets" }),
    );
    await userEvent.click(
      screen.getByRole("tab", { name: "Notes & activity" }),
    );
    expect(screen.getByLabelText("Add a note")).toHaveValue(
      "Unsent investigation context",
    );
    screen.getByRole("tab", { name: "Notes & activity" }).focus();
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Investigation" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("is read-only for viewers", async () => {
    mockApi([
      { path: "/api/v1/me", body: { ...ME, role: "VIEWER" } },
      { path: "/api/v1/cases/c1", body: baseCase },
      {
        path: "/api/v1/transactions/t1/risk",
        status: 404,
        body: { error: { code: "not_found", message: "not scored" } },
      },
    ]);
    renderWithProviders(
      <Routes>
        <Route path="/cases/:id" element={<CaseDetailPage />} />
      </Routes>,
      { route: "/cases/c1" },
    );
    await userEvent.click(
      await screen.findByRole("tab", { name: "Decision & approvals" }),
    );
    expect(
      await screen.findByText(/can view cases but not change them/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Resolve case" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Claim for review" }),
    ).not.toBeInTheDocument();
  });
});
