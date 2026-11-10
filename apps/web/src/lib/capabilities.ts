import { STATIC_DEMO } from "./staticDemo";

/** Build capabilities describe availability; server authorization remains authoritative. */
export const CAPABILITIES = {
  dashboard: { title: "Command Center", static: true },
  transactions: { title: "Transactions", static: true },
  cases: { title: "Investigations", static: true },
  model: { title: "Risk Intelligence", static: true },
  policy: { title: "Policy Lab", static: false },
  monitoring: { title: "Monitoring", static: false },
  network: { title: "Relationship explorer", static: false },
  refunds: { title: "Refund review", static: false },
  disputes: { title: "Dispute preparation", static: false },
  checkout: { title: "Sandbox checkout", static: false },
  settings: { title: "Integration & account", static: false },
  demo: { title: "Demo guide", static: false },
  operations: { title: "Operations", static: false },
  investigation: { title: "Investigation runs", static: false },
  evidence: { title: "Evidence & packets", static: false },
  decision: { title: "Decision & approvals", static: false },
} as const;
export type Capability = keyof typeof CAPABILITIES;
export function supports(capability: Capability): boolean {
  return !STATIC_DEMO || CAPABILITIES[capability].static;
}
export const FULL_APPLICATION_REQUIRED =
  "Requires the full application. This read-only static demo includes recorded payments, assessments and case facts. This feature needs an authenticated backend and is unavailable here. No action has been performed.";
