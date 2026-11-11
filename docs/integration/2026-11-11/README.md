# SENTINEL V2 and Antigravity integration

Status: validation in progress. This document will record executed results before review.

DESIGN APPROVAL: APPROVED
DEPLOYMENT APPROVAL: PENDING

## Exact sources and strategy

- UI: local `redesign/sentinel-v2`, `dd5e790ca2273598b3eecd40d473d8f567aa98bc` (27 commits beyond the common ancestor).
- Implementation: GitHub `main`, `482985f9cfc1ceee8cda9e700b959602874c494e` (14 commits beyond the common ancestor). `fix/gemini-400-recovery` and `backup/release-candidate-checkpoint` both resolve to implementation parent `3072f185042a6bcd1fdada294248bf8bba2426c4`; main additionally preserves its competitive audit and submission documents.
- Common ancestor: `410109c9304e11d2e1e685600194e290d978c0ab`.
- Isolated branch: `integration/sentinel-v2-antigravity-20261111`, worktree `/workspace/SENTINEL-integration`.
- Merge checkpoint: `cfd096e`, main first parent and approved UI second parent. Both source histories are retained. Source branches, main and release tags are not rewritten.

Branch identity was established from actual fetched GitHub refs, commit history and file changes, not names alone. The existing UI worktree's `origin` is a local recovery repository; GitHub was fetched separately under `refs/remotes/github/`. Default GitHub branch is main. The original UI worktree was clean. See source-heads.json, the complete file-conflict-matrix.csv and categorized change-inventory.csv. All 250 changed paths at the merge checkpoint match their authoritative source's SHA256 exactly: 115 UI paths and 135 implementation paths, with zero overlapping edited paths. No source deletion or directory replacement was required.

## Before and after feature inventory

| Area | UI source | Implementation source | Integrated result |
|---|---|---|---|
| Public entry | Approved ivory/purple wallet and receipt narrative, real scroll-linked reveal, reduced motion/mobile/skip | Original operational entry | Approved homepage at `/`; distinct demo and authenticated entry |
| Application navigation | Responsive horizontal shell, canonical `/app`, compatible legacy routes, query/hash sign-in restoration | Existing server endpoints | All redesigned routes retained; existing services unchanged |
| Auth and account | Redesigned sign-in/session expiry, permission boundaries | Sessions, CSRF, merchant isolation and role checks | New presentation with unchanged server enforcement |
| Transactions/dossier | Search/filter/sort/page/keyboard, bounded grid, stable loading, recorded timeline/risk/references | Checkout/provider summaries and scoring invariants | Full record data and controls retained |
| Investigations | Queue, case tabs, evidence upload/download, packets, notes, assignments and decisions | Gemini schema/modality adapter, multi-turn harness, safe diagnostics/budgets | Redesigned workbench uses existing hooks and improved provider implementation |
| Recovery | Refund review/independent approvals; labelled dispute drafts | Guarded payment execution, evidence/audit/state invariants | Existing controls, backend safety rules and disabled defaults retained |
| Policy, model, monitoring/network | Redesigned views, validation-only policy governance, grounded recorded model/factors | Same trained model, thresholds/calibration, scoped services | No scientific output or policy activation changes |
| Checkout and callbacks | Redesigned fixture/sandbox checkout | PayPal return/cancel URLs, approval URL persistence, escaping and URL validation | New React checkout plus original backend-owned callback HTML; no genuine provider execution in validation |
| Operations/webhooks | Redesigned operations diagnostics | Bridge retry transport, receipt/scoring idempotency and portable supervisor | UI consumes preserved endpoints; offline bridge invariants tested |
| Static and rollback | Snapshot closure/build gate, read-only capabilities, stable loading/CSP/hash/Pages navigation | Implementation changes confined to operational backend | Existing complete static payload retained byte-for-byte |

There are no divergent dependency edits: implementation leaves frontend package/lock files unchanged; UI adds pinned fonts and GSAP. `npm ci` is authoritative. Backend pins remain unchanged; a fresh isolated Python environment was installed from `apps/api[dev,ml]`, with resolved installation output retained. No trained artifacts, database migration files, business logic, backend security settings, CORS policy, payment rules, webhook signatures or fraud thresholds were changed by integration.

## Semantic reconciliation after the clean merge

1. Regenerated OpenAPI JSON and TypeScript from the actual merged backend. Main had added `/api/v1/paypal/return` and `/api/v1/paypal/cancel` without updating generated contracts. These are the only added paths; all previous paths and component schemas remain identical. No endpoint behavior was changed to accommodate the frontend.
2. Mechanical formatting/import cleanup in nine API test files and line wrapping in `ml/tests/test_pipeline.py` address source CI failures. Assertions and tolerances are unchanged; normalized executable AST comparisons are retained. No timeout was increased. The initial full API run also exposed an existing CI-directory import failure for the root `scripts` package; pytest now includes the repository root through test-only `pythonpath` configuration. Backend dependency pins and runtime application code are unchanged. GitHub’s minimal Supabase CI environment also omitted SQLAlchemy required by fixture URL safety tests; that job now installs the existing API-pinned SQLAlchemy version. No test or safety gate is skipped.
3. The deep-link browser regression now resolves a genuine seeded record via an isolated API request context instead of using a previous workspace's UUID. It still verifies unauthenticated redirect, exact canonical URL/query/hash, actual amount and refresh.
4. Added `scripts/prepare_integration_browser.py` to make viewer refund/dispute fixture prerequisites reproducible. It refuses non-loopback databases, names outside `_integration_browser_test`, non-fixture gateways, configured AI and enabled refund execution. It uses existing seed/judge/services, selects an eligible captured payment and creates only labelled local examples. No financial execution/provider calls occur.

The complete React source, font/design tokens and build configuration remain identical to approved UI source. Backend application code remains identical to implementation source. New backend-owned return/cancel HTML retains its original presentation; it is outside React's design system. Its informational text is not independent evidence of payment approval/capture: trust server-verified records. The old competitive audit and Devpost prose are preserved as authored; retaining them does not independently substantiate every historical claim.

## Recovery and promotion boundary

Immutable local refs: `backup/integration-20261111-main-482985f`, `backup/integration-20261111-implementation-3072f18`, `backup/integration-20261111-ui-dd5e790`. Full before/final bundles and validation evidence are outside public assets. Restore into a *new* directory with `git clone PATH/TO/before.bundle NEW-DIRECTORY`, or add a worktree from a backup ref. Do not reset a user's working tree.

Only the isolated integration branch may be pushed and a draft PR opened. Main, both source branches and tags remain unchanged. Closing the unmerged PR requires no production rollback. Any later main merge or production revert is a separate reviewed action. No deployment, live transaction, billable inference, hosted SQL, destructive operational migration, source branch rewrite or hosting change is performed here.

Pages and container publication remain manual under the existing workflow guards. The pre-existing `render.yaml` contains `autoDeploy: true`; actual hosting account settings are not inspected/changed. A future main merge must account for any connected hosting automation. No production approval follows from a local integration or test pass.
