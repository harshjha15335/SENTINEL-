import { screen } from "@testing-library/react";

import { ME, mockApi, renderWithProviders } from "@/test/utils";

import { RiskPanel } from "./RiskPanel";

const assessment = {
  id: "a1",
  transaction_id: "t1",
  model_version: "operational-v1",
  feature_version: "op-features-v1",
  risk_score: 0.231,
  risk_band: "HIGH",
  policy_decision: "ESCALATE",
  policy_mode: "SHADOW",
  thresholds: { medium: 0.0558, high: 0.1036 },
  feature_snapshot: {},
  explanation: {
    method: "xgboost_tree_shap",
    space: "log_odds_before_calibration",
    base_value: -2.1,
    raw_probability: 0.6,
    contributions: [
      { feature: "cust_txn_count_1h", label: "Payments from this payer in the previous hour", value: 3, contribution: 1.4 },
      { feature: "is_new_customer", label: "No earlier payment from this payer in 90 days", value: 0, contribution: -0.3 },
    ],
  },
  limitations: ["Trained on synthetic data only."],
  data_origin: "SYNTHETIC_DEMO",
  trigger: "demo_load",
  created_at: "2026-10-10T12:00:00Z",
  assessment_type: "MODEL_GENERATED",
};

describe("RiskPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("labels the score as model-generated and the policy as shadow-only", async () => {
    mockApi([
      { path: "/api/v1/me", body: ME },
      { path: "/api/v1/transactions/t1/risk", body: assessment },
    ]);
    renderWithProviders(<RiskPanel transactionId="t1" scorable />);
    expect(await screen.findByText("23.1%")).toBeInTheDocument();
    expect(screen.getByText("Model-generated")).toBeInTheDocument();
    expect(screen.getByText(/would send to the review queue/)).toHaveTextContent(/never blocks, captures or reverses/);
    expect(screen.getByText("raises 1.40")).toBeInTheDocument();
    expect(screen.getByText("lowers 0.30")).toBeInTheDocument();
  });

  it("shows no number when a payment has not been scored, and viewers cannot score", async () => {
    mockApi([
      { path: "/api/v1/me", body: { ...ME, role: "VIEWER" } },
      { path: "/api/v1/transactions/t1/risk", status: 404, body: { error: { code: "not_found", message: "This payment has not been scored" } } },
    ]);
    renderWithProviders(<RiskPanel transactionId="t1" scorable />);
    expect(await screen.findByText("Not scored")).toBeInTheDocument();
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Score this payment" })).not.toBeInTheDocument();
  });
});
