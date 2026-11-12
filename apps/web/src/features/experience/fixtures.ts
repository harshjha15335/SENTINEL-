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
    step: "01",
    label: "The wallet",
    title: "Every payment",
    subtitle: "has a story.",
    text: "Not every story ends well.",
  },
  {
    step: "02",
    label: "Money escapes",
    title: "Money moves.",
    subtitle: "The story begins.",
    text: "Open the wallet. Follow a simulated payment as it joins the flow.",
  },
  {
    step: "03",
    label: "Follow the money",
    title: "Look beyond",
    subtitle: "the amount.",
    text: "A payment carries context. Its timing, history and amount help tell the story.",
  },
  {
    step: "04",
    label: "Something is wrong",
    title: "One transaction",
    subtitle: "doesn’t add up.",
    text: "One payment breaks from the pattern. A reason to look closer, never a verdict on intent.",
  },
  {
    step: "05",
    label: "Risk analysis",
    title: "The signal",
    subtitle: "was always there.",
    text: "SENTINEL brings it into focus. Seven past-day payments and an 8.4× amount deviation, in one illustrative example.",
  },
  {
    step: "06",
    label: "From money to evidence",
    title: "Less noise.",
    subtitle: "More context.",
    text: "The payment becomes a readable record. Facts, contributing signals and a timeline, ready for human review.",
  },
  {
    step: "07",
    label: "Product reveal",
    title: "Your next move,",
    subtitle: "better informed.",
    text: "Enter the workspace. Trace the payment. Make the decision.",
  },
] as const;
