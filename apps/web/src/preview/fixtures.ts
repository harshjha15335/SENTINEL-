import type { TransactionDetail } from "@/lib/api";

/** v1: authored, public-safe examples. Scores are illustrative, never model inference. */
export const FIXTURE_VERSION = "sentinel-public-v1";
export const examples = [
  {
    id: "dossier-0148",
    label: "Amount deviation",
    amount: 184900,
    band: "HIGH",
    score: 0.87,
    product: "Studio equipment",
    payer: "DEMO-PAYER-148",
    factors: [
      ["Amount vs merchant median", "8.4×", 84],
      ["Customer transactions · past 24h", "7", 67],
      ["New customer", "Yes", 44],
    ],
  },
  {
    id: "dossier-0149",
    label: "Established pattern",
    amount: 24900,
    band: "LOW",
    score: 0.12,
    product: "Team workspace",
    payer: "DEMO-PAYER-149",
    factors: [
      ["Amount vs merchant median", "1.1×", 11],
      ["Customer transactions · past 24h", "1", 10],
      ["New customer", "No", 0],
    ],
  },
] as const;
export function fixtureTransaction(index: number): TransactionDetail {
  const e = examples[index] ?? examples[0];
  return {
    id: e.id,
    amount_minor: e.amount,
    currency: "USD",
    data_origin: "SIMULATED",
    status: "CAPTURED",
    created_at: "2026-11-01T10:42:00Z",
    updated_at: "2026-11-01T10:43:00Z",
    occurred_at: "2026-11-01T10:43:00Z",
    paypal_order_id: `DEMO-ORDER-${e.id}`,
    paypal_capture_id: `DEMO-CAPTURE-${e.id}`,
    payer_reference: e.payer,
    product_name: e.product,
    quantity: 1,
    failure_reason: null,
    provider_status: "COMPLETED",
    provider_summary: {},
    risk_band: e.band,
    risk_score: e.score,
    audit: [],
    events: [],
  };
}
export const storyStages = [
  {
    step: "00",
    label: "The anatomy of fraud",
    title: "Fraud leaves a pattern.",
    subtitle: "SENTINEL reads it.",
    text: "Explore the signals, decisions, and evidence behind every suspicious transaction.",
  },
  {
    step: "01",
    label: "Transaction received",
    title: "A transaction.",
    subtitle: "A thousand questions.",
    text: "Follow a simulated payment through the evidence transport. Every field has a source. Every signal has context.",
  },
  {
    step: "02",
    label: "Signal extraction",
    title: "Patterns",
    subtitle: "become visible.",
    text: "The tape leaves the machine. A simulated $1,849 payment, seven past-day payments, and an 8.4× amount deviation travel along one evidence path.",
  },
  {
    step: "03",
    label: "Risk evaluation",
    title: "Signals become",
    subtitle: "intelligence.",
    text: "The connected signals assemble into an illustrative 87/100 assessment. This demonstration is not live inference and does not establish intent.",
  },
  {
    step: "04",
    label: "Investigation assembly",
    title: "Every decision",
    subtitle: "deserves evidence.",
    text: "Bring transaction context, review status, and an accountable case history into one investigation workspace.",
  },
  {
    step: "05",
    label: "Workspace reveal",
    title: "From first signal",
    subtitle: "to final decision.",
    text: "A clear record. An explainable assessment. A focused workspace for the human behind the decision.",
  },
] as const;
