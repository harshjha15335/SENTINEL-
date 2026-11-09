# Authoritative feature and workflow matrix

Baseline `410109c`. PRESENT/PARTIAL/ABSENT describe implementation; PASSED/FAILED/NOT TESTED/BLOCKED describe verification. PASSED below means relevant **local automated** behavior, not real-provider verification or complete browser coverage. Every original UI is retained in Phase 1. Phase 2 cannot delete blocked features until replacement parity is established.

| ID | Feature / current route | Implementation | Verification | UI / state source under apps/web/src/features | Logic under apps/api | Roles / inputs / supported actions | Existing verification |
|---|---|---|---|---|---|---|---|
| AUTH | Authentication: `/login` | PRESENT | PASSED (local automated) | `auth/LoginPage.tsx`; `auth/session.ts` | `app/auth; app/api/v1/auth.py` | All users; authenticated logout. Email/password; login, logout, expiry; cookies and role-scoped /me | API tests/test_health_auth.py; web auth/LoginPage.test.tsx |
| DASH | Command Center: `/` | PRESENT | PASSED (local automated) | `dashboard/DashboardPage.tsx`; `dashboard/DashboardPage.tsx` | `app/services/dashboard.py` | Any member. Load grouped origin-safe totals; navigate recent payment/case | API tests/test_risk_cases.py; web dashboard/DashboardPage.test.tsx |
| TX | Transactions: `/transactions` | PRESENT | PASSED (local automated) | `transactions/TransactionsPage.tsx`; `transactions/useTransactions.ts` | `app/services/transactions.py` | Any member. q/status/origin/page; submit search, filter, sort current grid, paginate, select row | API tests/test_risk_cases.py; browser coverage varies, see QA |
| DOS | Payment detail: `/transactions/:id` | PRESENT | PASSED (local automated) | `transactions/TransactionDetailPage.tsx`; `transactions/useTransactions.ts` | `app/services/transactions.py` | Any member. Transaction UUID; facts, provider refs, events/audit, origin and associated cases | API tests/test_risk_cases.py; browser coverage varies, see QA |
| RISK | Scoring and explanations: `/transactions/:id; /cases/:id` | PRESENT | PASSED (local automated) | `risk/RiskPanel.tsx`; `risk/useRisk.ts` | `app/services/risk; ml/sentinel_ml` | Read any member; rescore ADMIN/ANALYST. Read latest assessment; optional score/rescore; show actual SHAP factors and shadow recommendation | API tests/test_risk_cases.py; web risk/RiskPanel.test.tsx |
| CASE | Review queue/case actions: `/cases; /cases/:id` | PRESENT | PASSED (local automated) | `cases/CaseDetailPage.tsx`; `cases/useCases.ts` | `app/services/cases.py` | Read any member; mutate ADMIN/ANALYST plus assignment rules. Filter status/priority/origin/mine/transaction; open, claim, add note, resolve with existing note/resolution validation | API tests/test_risk_cases.py; web cases/CaseDetailPage.test.tsx |
| INV | Investigation runs: `/cases/:id` | PRESENT | PASSED (local automated) | `investigation/InvestigationPanel.tsx`; `investigation/useWorkbench.ts` | `app/services/investigation` | Read any member; start ADMIN/ANALYST. Start auto/deterministic run; poll queued/running; read findings, sources, tool calls, budgets, failures | API tests/test_investigations.py; web investigation/Workbench.test.tsx |
| EVID | Evidence/checklist: `/cases/:id` | PRESENT | PASSED (local automated) | `investigation/EvidencePanel.tsx`; `investigation/useWorkbench.ts` | `app/services/evidence; app/services/storage.py` | Read/download any member; upload ADMIN/ANALYST. File/category/description; existing MIME/size/content validation; list and private download; duplicate rejection | API tests/test_evidence_packets.py; web investigation/Workbench.test.tsx |
| PACK | PDF packets: `/cases/:id` | PRESENT | PASSED (local automated) | `investigation/PacketPanel.tsx`; `investigation/useWorkbench.ts` | `app/services/packets.py` | Read/download any member; generate ADMIN/ANALYST. Generate immutable evidence packet; list and private download; no public attachment URLs | API tests/test_evidence_packets.py; web investigation/Workbench.test.tsx |
| APPR | Approval workflow: `/cases/:id` | PRESENT | PASSED (local automated) | `investigation/ApprovalsPanel.tsx`; `investigation/useWorkbench.ts` | `app/services/approvals.py` | Operator plus independent decision/service constraints. Action/packet/rationale; request approval, approve/reject; immutable decision/audit; no autonomous payment | API tests/test_approvals.py; web investigation/Workbench.test.tsx |
| MODEL | Model intelligence: `/model` | PRESENT | PASSED (local automated) | `risk/ModelPage.tsx`; `risk/useRisk.ts` | `app/services/risk; ml/artifacts` | Any member. Model card/version, evaluation and capacity metadata; genuine synthetic training boundaries | API tests/test_risk_cases.py; browser coverage varies, see QA |
| POL | Policy simulation/governance: `/policy` | PRESENT | PASSED (local automated) | `policy/PolicyLabPage.tsx`; `policy/PolicyLabPage.tsx` | `app/services/policy.py` | Read any member; create/submit operator; independent ADMIN decides. Threshold/capacity/cost inputs; baseline/proposed metrics; reset; save/submit/decide shadow draft; no activation | API tests/test_policy_lab.py; browser coverage varies, see QA |
| MON | Risk monitoring: `/monitoring` | PRESENT | PASSED (local automated) | `monitoring/MonitoringPage.tsx`; `monitoring/MonitoringPage.tsx` | `app/services/monitoring.py` | Any member. Origin/window/capacity; monitoring distributions, cohort changes, unscored/coverage states | API tests/test_monitoring.py; web monitoring/MonitoringPage.test.tsx |
| NET | Relationship explorer: `/network` | PRESENT | PASSED (local automated) | `network/NetworkPage.tsx`; `network/NetworkPage.tsx` | `app/services/monitoring.py` | Any member. Origin/window/limit/payer/band; scoped payer/transaction graph; select node; no identity/device intelligence | API tests/test_monitoring.py; web network/NetworkPage.test.tsx |
| OPS | Operations: `/operations` | PRESENT | PASSED (local automated) | `operations/OperationsPage.tsx`; `operations/OperationsPage.tsx` | `app/api/v1/operations.py; app/services/worker_health.py` | ADMIN; global inbox additionally installation-merchant scoped. Inspect heartbeat, queues, age/error/retry aggregates; no fabricated healthy status | API tests/test_operations.py; web operations/OperationsPage.test.tsx |
| REF | Refund review: `/refunds?case=:id` | PRESENT | PASSED (local automated) | `refunds/RefundsPage.tsx`; `refunds/RefundsPage.tsx` | `app/services/refunds.py` | Read any member; request operator; independent ADMIN decision/execution. Case/amount request; history/snapshot; approve/reject; execution is guarded and disabled by default | API tests/test_refunds.py; web refunds/RefundsPage.test.tsx |
| DIS | Dispute preparation: `/disputes?case=:id` | PRESENT | PASSED (local automated) | `disputes/DisputesPage.tsx`; `disputes/DisputesPage.tsx` | `app/services/disputes.py` | Read any member; create/assign/draft operator; sync ADMIN. List/select/checklist, labeled demo, read-only sync, assign self, generate/download draft; external submit disabled | API tests/test_disputes.py; web disputes/DisputesPage.test.tsx |
| CHECK | Sandbox/fixture checkout: `/checkout` | PRESENT | PASSED (local automated) | `checkout/CheckoutPage.tsx`; `checkout/useCheckout.ts` | `app/services/paypal; app/api/v1/paypal.py` | ADMIN/ANALYST to mutate. Choose catalogue item/quantity; order/capture via gateway and idempotency; fixture origin SIMULATED | API tests/test_checkout.py; web checkout/CheckoutPage.test.tsx |
| SET | Integration diagnostics/audit: `/settings` | PRESENT | PASSED (local automated) | `settings/SettingsPage.tsx`; `settings/usePayPalStatus.ts` | `app/api/v1/paypal.py; app/api/v1/audit.py` | Any member status; ADMIN audit. PayPal/AI configuration and account access; masked/server-safe status; paged audit. No credential-edit form found | API tests/test_sandbox_gateway.py; browser coverage varies, see QA |
| DEMO | Private demo guide: `/demo` | PRESENT | PASSED (local automated) | `operations/DemoGuidePage.tsx`; `operations/DemoGuidePage.tsx` | `app/services/demo/judge.py` | DEMO merchant; viewer-safe. Read prepared scenario; follow investigation and packet links without write controls | API tests/test_judge_demo.py; browser coverage varies, see QA |

## External and intentionally absent capabilities

| Capability | Implementation | Verification | Preservation / scope |
|---|---|---|---|
| Genuine PayPal sandbox events, OAuth, captures and real refund execution | PRESENT | BLOCKED | Keep gateway, signature verification, durable ingestion and guards. Local fixture/mocked tests do not establish real-provider success. No provider calls in this phase. |
| Paid AI inference through configured providers | PRESENT | BLOCKED | Preserve provider adapters, validation, budgets and deterministic fallback. No paid call to validate a visual prototype. |
| Public production hosting/worker health | PRESENT configuration | NOT TESTED | No deployment; local heartbeat is not production health. |
| Policy activation | ABSENT by design | NOT TESTED | Shadow proposals never change serving threshold. |
| External dispute submission | PARTIAL (explicit disabled endpoint) | PASSED (rejection guards) | Preserve preparation/download; do not present submission as working. |
| Standalone integrations/configuration editor | ABSENT | NOT TESTED | Existing diagnostics are under settings. Do not invent new settings mutation APIs. |
| Device fingerprint/geolocation/identity graph | ABSENT | NOT TESTED | Relationship graph is merchant-scoped shared-payer context only. |

## Data contracts and provenance

Canonical contracts: `packages/contracts/openapi.json` and `.ts`; `src/lib/api.ts` aliases those generated types. Transactions, cases, assessments and aggregate groups carry origin. Normal operational records come from authorized API/DB; the existing Pages build uses `public/demo` snapshots through staticApi and refuses writes. Do not mix origins into new aggregate metrics. The V2 public fixtures use only supported fields and visibly illustrative scores, not an alternate scoring engine. Existing trained outputs and artifacts are unchanged.

Source inspection found no general offline cache, unsaved-edit guard or application-wide stale-data warning; absence is recorded in the state matrix, not silently invented.

## Action-level acceptance contracts

Common preconditions: existing merchant session and permitted server role; valid scoped record for detail/action workflows. Expected API interactions use `/api/v1` with unchanged CSRF on writes. Invalid inputs must remain rejected by existing validation; 401/403/404/409/422/provider errors must never become successful demo data. Preserve existing URL/query and cache invalidation behavior. Applicable new regression tests must cover both success and failure; read-only prototype screens do not implement mutating actions yet.

### AUTH-1
- Entry route: `/login`. User role: Any.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: email/password. Actions: Submit login, then logout.
- Expected API interactions: `POST /auth/login; GET /me; POST /auth/logout`.
- Expected visible outputs: Correct merchant/role and requested destination; session cleared on logout.
- Error cases: Invalid credentials, rate limit, expired session, CSRF.
- URL/session behavior: Router state from pathname; existing 8h session.
- Existing tests: health_auth; LoginPage; fixture-flow. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### TX-1
- Entry route: `/transactions`. User role: Any member.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: q/status/origin/page. Actions: Submit search, filter, paginate, sort, open row.
- Expected API interactions: `GET /transactions?limit&offset&q&status&data_origin`.
- Expected visible outputs: Matching records and total; selected transaction route.
- Error cases: Empty results; malformed filters; network/403.
- URL/session behavior: q/status/origin/page persisted; sorting remains grid-local.
- Existing tests: risk_cases; fixture-flow. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### DOS-1
- Entry route: `/transactions/:id`. User role: Any member.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Scoped UUID. Actions: Inspect facts, events, risk and associated cases.
- Expected API interactions: `GET /transactions/:id; GET /transactions/:id/risk; GET /cases?transaction_id`.
- Expected visible outputs: Actual values, recorded events, no score if none; case links.
- Error cases: 404 missing record/assessment; 401/403; risk can fail separately.
- URL/session behavior: Direct id route and browser navigation preserved.
- Existing tests: risk_cases; v2-integration. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### RISK-1
- Entry route: `Payment/case detail`. User role: ADMIN/ANALYST.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Scorable transaction. Actions: Score or rescore.
- Expected API interactions: `POST /transactions/:id/risk`.
- Expected visible outputs: Stored assessment, model/version/explanations; caches refreshed.
- Error cases: Viewer denied; unscorable input; model error.
- URL/session behavior: Current record retained; no fake score.
- Existing tests: risk_cases; RiskPanel. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### CASE-1
- Entry route: `/cases`. User role: Any member.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: status/priority/origin/mine/page. Actions: Filter queue, open case.
- Expected API interactions: `GET /cases with current params; GET /cases/:id`.
- Expected visible outputs: Correct merchant queue and selected case.
- Error cases: Empty queue; forbidden or missing case.
- URL/session behavior: Existing route/filter semantics.
- Existing tests: risk_cases; fixture-flow. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### CASE-2
- Entry route: `Case detail`. User role: Operator with assignment rules.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: transaction/reason; claim; resolution/note; note body. Actions: Open, claim, add note or resolve.
- Expected API interactions: `POST /cases; /cases/:id/claim; /notes; /resolve`.
- Expected visible outputs: Valid state transition, notes and audit update.
- Error cases: Viewer/cross-tenant denied; invalid or duplicate state; validation.
- URL/session behavior: Cache invalidation preserved; forms do not retry writes automatically.
- Existing tests: risk_cases; CaseDetailPage. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### INV-1
- Entry route: `Case detail`. User role: Operator.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: auto or deterministic mode. Actions: Start run and inspect result.
- Expected API interactions: `POST/GET /cases/:id/investigations; GET findings/run`.
- Expected visible outputs: Queued/running polls; success findings or honest failed state.
- Error cases: Unavailable provider; limits/timeout/duplicate/prompt injection.
- URL/session behavior: Poll only active runs, scoped case id.
- Existing tests: investigations; investigation_next_phase; Workbench. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### EVID-1
- Entry route: `Case detail`. User role: Operator upload; member read.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: file/category/description. Actions: Upload, list, inspect checklist, download.
- Expected API interactions: `POST/GET /cases/:id/evidence; private download`.
- Expected visible outputs: Artifact belongs to correct case; private file and checklist.
- Error cases: Size/type/content/duplicate validation; unauthorized download.
- URL/session behavior: Existing multipart/CSRF and no duplicate auto-retry.
- Existing tests: evidence_packets; Workbench; workbench e2e. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### PACK-1
- Entry route: `Case detail`. User role: Operator generate; member read.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Case and current evidence. Actions: Generate/list/download packet.
- Expected API interactions: `POST/GET /cases/:id/packets; packet download`.
- Expected visible outputs: Immutable PDF snapshot and provenance.
- Error cases: Missing evidence; scoped access; generation failure.
- URL/session behavior: Private same-origin cookie-authorized download.
- Existing tests: evidence_packets; Workbench; workbench e2e. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### APPR-1
- Entry route: `Case detail`. User role: Operator plus independent decision.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: action/rationale/packet; approve/reject. Actions: Request and decide approval.
- Expected API interactions: `POST/GET approvals and decision endpoints`.
- Expected visible outputs: Independent immutable decision with audit; no payment execution.
- Error cases: Self-decision, duplicates, invalid state, tenant scope.
- URL/session behavior: Preserve backend separation of duties.
- Existing tests: approvals; Workbench; workbench e2e. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### POL-1
- Entry route: `/policy`. User role: Member simulation; operator proposal; ADMIN decision.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Threshold/capacity/cost assumptions; name/rationale. Actions: Simulate, reset, save, submit, independently decide.
- Expected API interactions: `GET /policy-lab/simulate; GET/POST drafts; submit/decide`.
- Expected visible outputs: Consistent baseline/proposal over validation split; shadow-only snapshot.
- Error cases: Out-of-range inputs; self-decision; model unavailable.
- URL/session behavior: Controls currently component state; do not invent URL persistence.
- Existing tests: policy_lab; next_phase_invariants. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### MON-1
- Entry route: `/monitoring; /network`. User role: Member.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Origin/window/capacity or payer/band/limit. Actions: Inspect cohorts/graph, change scope, select node.
- Expected API interactions: `GET /monitoring/risk; GET /network`.
- Expected visible outputs: Scoped aggregate/graph, readable limitations and empty state.
- Error cases: No data, truncated graph, network failure.
- URL/session behavior: Existing local filter/selection behavior.
- Existing tests: monitoring; MonitoringPage; NetworkPage. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### OPS-1
- Entry route: `/operations`. User role: ADMIN.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Existing merchant scope. Actions: Inspect queue and worker heartbeats.
- Expected API interactions: `GET /operations/webhooks`.
- Expected visible outputs: Actual age/readiness/error state, no invented green status.
- Error cases: Viewer denied; stale/degraded/missing worker; DB failure.
- URL/session behavior: Existing bounded polling and role gate.
- Existing tests: operations; OperationsPage; operations e2e. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### REF-1
- Entry route: `/refunds?case`. User role: Operator request; independent ADMIN decision.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Case/amount; decision/snapshot. Actions: Request, inspect history, approve/reject.
- Expected API interactions: `GET refunds/history; POST case refunds; POST decision`.
- Expected visible outputs: Immutable financial intent, role-safe controls, unchanged execution guard.
- Error cases: Already refunded; over amount; duplicate/self decision; stale snapshot.
- URL/session behavior: Keep case query and CSRF/idempotency; no provider execution for UI tests.
- Existing tests: refunds; RefundsPage. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### DIS-1
- Entry route: `/disputes?case`. User role: Member read; operator prepare; ADMIN sync.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Case; selected dispute; assignment. Actions: List/select, labeled demo, assign, draft/download, read-only sync.
- Expected API interactions: `GET disputes/detail; POST demo/sync/assign/drafts; GET download`.
- Expected visible outputs: Checklist/draft contextual data; explicit external submit unavailable.
- Error cases: Viewer write denied; invalid attachment; provider sync unavailable.
- URL/session behavior: Case query/current selection semantics retained.
- Existing tests: disputes; DisputesPage. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### CHECK-1
- Entry route: `/checkout`. User role: Operator.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Catalogue product and quantity. Actions: Create order, approve/capture in local fixture only.
- Expected API interactions: `GET catalogue/status; POST paypal/orders and capture`.
- Expected visible outputs: Server-authoritative amount, proper provenance and idempotency.
- Error cases: SDK/provider errors, duplicate capture, invalid quantity.
- URL/session behavior: Preserve existing status flow and no client-supplied amount.
- Existing tests: checkout; CheckoutPage; fixture-flow. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### SET-1
- Entry route: `/settings`. User role: Member status; ADMIN audit.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: None, audit page. Actions: Inspect diagnostics/account/audit.
- Expected API interactions: `GET paypal/status; /ai/status; /me; /audit`.
- Expected visible outputs: Honest configured/unavailable status, restricted audit.
- Error cases: No secret exposure; provider check failure; unauthorized audit.
- URL/session behavior: No nonexistent credential-edit action.
- Existing tests: sandbox_gateway; health_auth; fixture-flow. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

### DEMO-1
- Entry route: `/demo`. User role: Prepared DEMO merchant viewer.
- Preconditions: scoped authenticated session and existing relevant record; catalogue/scenario/model artifacts where applicable.
- Inputs: Provisioned scenario. Actions: Follow prepared case/packet.
- Expected API interactions: `GET /demo/scenario and scoped reads`.
- Expected visible outputs: Labeled synthetic scenario; no financial/write controls.
- Error cases: Non-DEMO/foreign tenant denied.
- URL/session behavior: Deep links preserved; demo is separate from live merchant.
- Existing tests: judge_demo; operations e2e. Required V2 regression: repeat these behavior assertions through the replacement UI, including denied roles/error states; retain valid original coverage until then.

