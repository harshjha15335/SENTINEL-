import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ME, mockApi, renderWithProviders } from "@/test/utils";

import { ApprovalsPanel } from "./ApprovalsPanel";
import { EvidencePanel } from "./EvidencePanel";
import { InvestigationPanel } from "./InvestigationPanel";

const TXN = "11111111-1111-1111-1111-111111111111";
const ASSESS = "22222222-2222-2222-2222-222222222222";

const findings = {
  summary: "Deterministic summary — AI provider unavailable. $42.00 captured payment.",
  verified_facts: [{ statement: "Payment of 42.00 USD", sources: [{ kind: "transaction", id: TXN }] }],
  risk_indicators: [{ description: "Prior refunds moved the score up", sources: [{ kind: "risk_assessment", id: ASSESS }] }],
  counter_indicators: [],
  evidence_references: [],
  missing_information: ["Proof of shipment or delivery"],
  limitations: ["No AI analysis was performed."],
  recommended_action: "REQUEST_MORE_EVIDENCE",
  recommendation_rationale: "High risk and no evidence attached.",
  human_approval_required: true,
};

function run(overrides: Record<string, unknown> = {}) {
  return {
    id: "r1",
    case_id: "c1",
    status: "COMPLETED",
    mode: "DETERMINISTIC",
    label: "Deterministic summary — AI provider unavailable",
    generated_by_ai: false,
    provider: "none",
    model_name: "deterministic",
    prompt_version: "deterministic-v1",
    findings,
    tool_calls: [
      { name: "get_transaction_details", arguments: {}, outcome: "ok", duration_ms: 2, records: [{ kind: "transaction", id: TXN }], note: null },
      { name: "get_related_disputes", arguments: {}, outcome: "unavailable", duration_ms: 0, records: [], note: "Phase 5" },
    ],
    source_refs: [{ kind: "transaction", id: TXN }],
    usage: {},
    error_category: null,
    error_message: null,
    data_origin: "SYNTHETIC_DEMO",
    initiated_by: { id: "u1", email: ME.email },
    created_at: "2026-10-11T10:00:00Z",
    started_at: "2026-10-11T10:00:00Z",
    completed_at: "2026-10-11T10:00:01Z",
    duration_ms: 900,
    ...overrides,
  };
}

const AI_OFF = { configured: false, provider: "none", model_name: null, fallback: "DETERMINISTIC" };

describe("InvestigationPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("labels a deterministic summary as not AI and shows grounded findings", async () => {
    mockApi([
      { path: "/api/v1/ai/status", body: AI_OFF },
      { path: "/api/v1/cases/c1/investigations", body: [run()] },
    ]);
    renderWithProviders(<InvestigationPanel caseId="c1" canRun />);
    expect(await screen.findByText("Deterministic summary — AI provider unavailable")).toBeInTheDocument();
    expect(screen.getByText("Rule-based")).toBeInTheDocument();
    expect(screen.queryByText("Model-generated")).not.toBeInTheDocument();
    expect(screen.getByText(/No language model was used/)).toBeInTheDocument();
    expect(screen.getByText("Request more evidence")).toBeInTheDocument();
    expect(screen.getByText(/SENTINEL has not acted on this/)).toBeInTheDocument();
    expect(screen.getByTitle(`Payment ${TXN}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate deterministic summary" })).toBeEnabled();
    expect(screen.getByText("AI provider not configured")).toBeInTheDocument();
  });

  it("shows a running state, then a failure with retry that starts a new run", async () => {
    const calls = mockApi([
      { path: "/api/v1/ai/status", body: { configured: true, provider: "anthropic", model_name: "claude-sonnet-5-5", fallback: null } },
      {
        path: "/api/v1/cases/c1/investigations",
        body: [
          run({ id: "r2", status: "FAILED", mode: "AI_AGENT", generated_by_ai: true, findings: null, error_category: "PROVIDER_TIMEOUT", error_message: "The AI provider did not finish within 90 seconds." }),
          run(),
        ],
      },
      { method: "POST", path: "/api/v1/cases/c1/investigations", status: 202, body: run({ id: "r3", status: "QUEUED", findings: null }) },
    ]);
    renderWithProviders(<InvestigationPanel caseId="c1" canRun />);
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/did not answer in time/)).toBeInTheDocument();
    expect(within(alert).getByText(/Earlier results are kept/)).toBeInTheDocument();
    // The previous completed findings stay visible.
    expect(screen.getByText("Payment of 42.00 USD")).toBeInTheDocument();
    await userEvent.click(within(alert).getByRole("button", { name: /Retry/ }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ mode: "auto" });
  });

  it("disables starting while a run is active and hides controls from viewers", async () => {
    mockApi([
      { path: "/api/v1/ai/status", body: AI_OFF },
      { path: "/api/v1/cases/c1/investigations", body: [run({ status: "RUNNING", findings: null, completed_at: null })] },
    ]);
    const { unmount } = renderWithProviders(<InvestigationPanel caseId="c1" canRun />);
    expect(await screen.findByRole("status")).toHaveTextContent("Summarising the case records");
    expect(screen.getByRole("button", { name: "Generate deterministic summary" })).toBeDisabled();
    unmount();

    renderWithProviders(<InvestigationPanel caseId="c1" canRun={false} />);
    expect(await screen.findByText(/can read investigations but not start them/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Generate|Run AI/ })).not.toBeInTheDocument();
  });
});

describe("EvidencePanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  const list = {
    items: [],
    checklist: [],
    max_bytes: 10 * 1024 * 1024,
    accepted_types: ["application/pdf", "image/jpeg", "image/png"],
  };

  it("uploads a PDF as multipart with the CSRF header", async () => {
    document.cookie = "sentinel_csrf=tok123";
    const calls = mockApi([
      { path: "/api/v1/cases/c1/evidence", body: list },
      {
        method: "POST",
        path: "/api/v1/cases/c1/evidence",
        status: 201,
        body: { id: "e1" },
      },
    ]);
    renderWithProviders(<EvidencePanel caseId="c1" canUpload />);
    expect(await screen.findByText("No evidence uploaded")).toBeInTheDocument();
    const file = new File(["%PDF-1.4"], "invoice.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Upload evidence"), file);
    await userEvent.selectOptions(screen.getByLabelText("What is it?"), "SHIPPING_PROOF");
    await userEvent.click(screen.getByRole("button", { name: "Upload" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    const post = calls.find((c) => c.method === "POST");
    expect(post?.headers["X-CSRF-Token"]).toBe("tok123");
    const form = post?.body as FormData;
    expect(form.get("category")).toBe("SHIPPING_PROOF");
    expect((form.get("file") as File).name).toBe("invoice.pdf");
  });

  it("refuses unsupported files before upload", async () => {
    mockApi([{ path: "/api/v1/cases/c1/evidence", body: list }]);
    renderWithProviders(<EvidencePanel caseId="c1" canUpload />);
    const input = await screen.findByLabelText("Upload evidence");
    await userEvent.upload(input, new File(["<svg/>"], "x.svg", { type: "image/svg+xml" }), { applyAccept: false });
    expect(screen.getByRole("alert")).toHaveTextContent("Only PDF, PNG and JPEG files are accepted.");
    expect(screen.getByRole("button", { name: "Upload" })).toBeDisabled();
  });
});

describe("ApprovalsPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  const pending = {
    id: "a1",
    case_id: "c1",
    transaction_id: "t1",
    action_type: "PREPARE_REFUND",
    action_snapshot: { amount_minor: 4200, currency: "USD", paypal_executable_reason: "SYNTHETIC_DEMO payment: there is no PayPal capture to refund." },
    snapshot_sha256: "a".repeat(64),
    required_roles: ["ADMIN"],
    justification: "Payer has prior refunds",
    status: "PENDING",
    requested_by: { id: "u1", email: ME.email },
    investigation_run_id: null,
    data_origin: "SYNTHETIC_DEMO",
    created_at: "2026-10-11T10:00:00Z",
    decided_at: null,
    decision: null,
    execution: null,
  };

  it("does not let the requester or a wrong role decide", async () => {
    mockApi([
      { path: "/api/v1/cases/c1/approvals", body: [pending] },
      { path: "/api/v1/cases/c1/packets", body: [] },
    ]);
    renderWithProviders(<ApprovalsPanel caseId="c1" me={ME as never} canRequest resolved={false} />);
    expect(await screen.findByText(/Full refund of \$42.00/)).toBeInTheDocument();
    expect(screen.getByText(/You cannot decide your own request/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("lets an admin approve with a note and shows that nothing was executed", async () => {
    const admin = { ...ME, id: "u2", email: "admin@northwind.example", role: "ADMIN" };
    const calls = mockApi([
      { path: "/api/v1/cases/c1/approvals", body: [pending] },
      { path: "/api/v1/cases/c1/packets", body: [] },
      {
        method: "POST",
        path: "/api/v1/cases/c1/approvals/a1/approve",
        body: { ...pending, status: "APPROVED" },
      },
    ]);
    renderWithProviders(<ApprovalsPanel caseId="c1" me={admin as never} canRequest resolved={false} />);
    const approve = await screen.findByRole("button", { name: "Approve" });
    expect(approve).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Decision note"), "Snapshot checked");
    await userEvent.click(approve);
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ comment: "Snapshot checked" });
  });

  it("creates a request without sending any amount", async () => {
    const calls = mockApi([
      { path: "/api/v1/cases/c1/approvals", body: [] },
      { path: "/api/v1/cases/c1/packets", body: [] },
      { method: "POST", path: "/api/v1/cases/c1/approvals", status: 201, body: pending },
    ]);
    renderWithProviders(<ApprovalsPanel caseId="c1" me={ME as never} canRequest resolved={false} />);
    await userEvent.click(await screen.findByLabelText(/Prepare refund/));
    await userEvent.type(screen.getByLabelText("Justification"), "Payer has prior refunds");
    await userEvent.click(screen.getByRole("button", { name: "Request approval" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({ action_type: "PREPARE_REFUND", justification: "Payer has prior refunds" });
  });
});
