# Phase 2 reconstruction and Gate 2 review

DESIGN APPROVAL: APPROVED (Gate 1, user instruction)
DEPLOYMENT APPROVAL: PENDING

The approved Follow the Money experience now leads into a reconstructed operational frontend. This report supersedes prototype-only scope and old pending Gate 1 statements. The exact source commit and final verification counts are in the delivery manifest accompanying the review archive.

## Application behavior

`/` is the public wallet story. `/demo-payment` is an explicitly simulated, authored public dossier; neither route reads merchant APIs. `/app` opens the existing authenticated merchant Command Center. Unauthenticated visitors reach sign-in and return to their requested path, query and fragment. Existing `/transactions`, `/cases`, `/model`, `/checkout`, `/demo`, `/operations`, `/refunds`, `/disputes`, `/policy`, `/monitoring`, `/network` and `/settings` routes redirect under `/app`, preserving the remaining path, query, fragment and router state. APIs retain their original paths. Existing signed-in users visiting `/` see the public story and can enter their workspace through its authenticated CTA. No records or sessions are migrated.

The root cutover followed the real investigation → evidence → packet → independent approval → audit test and broad desktop/mobile replacement checks. Production verification then repeats these workflows against the compiled frontend served by the existing API, rather than relying solely on Vite.

## Functionality preservation matrix

The action contracts in `02-feature-and-workflow-matrix.md` remain the baseline. All listed UI areas have replacements. Backend capabilities that were absent or blocked remain so; visual reconstruction does not certify providers.

| Baseline | New route / presentation | Preserved behavior and states | Verification evidence |
|---|---|---|---|
| AUTH | `/login`; global merchant/account bar | Email/password validation, rejection, merchant role, requested destination, logout, expiry, CSRF/session endpoints. Sign-out now updates the active session observer before removing private queries, preventing the previous screen from lingering. | LoginPage and session regression tests; fixture/workbench/functional browser tests; API health/auth tests |
| DASH | `/app`; priority decision desk and secondary ledgers | Real `/dashboard/summary`, origin-separated totals, actual high-priority `/cases` queue, recent record/case navigation; independent queue errors, loading and empty states | DashboardPage tests, fixture-flow, production screenshots |
| TX | `/app/transactions`; light full-width ledger | Order/capture search, explicit Search or Enter, status/origin/page URL state, 25-row pagination, current-page grid sorting, keyboard row entry, loading/empty/errors | Functional and integration browser tests; API risk/cases tests |
| DOS | `/app/transactions/:id`; payment casefile | Actual amount/currency/provider refs/origin; recorded event timeline or truthful empty state; recorded assessment and associated case links; missing/forbidden/session errors | Integration browser actual API/DB record assertions, axe, API tests |
| RISK | Dossier and case investigation tab | Recorded model score/bands, exact SHAP units/directions, version, limitations, real score/rescore and create review case; no invented provider judgment | RiskPanel unit tests, fixture-flow and functional rescore, API risk tests |
| CASE | `/app/cases`; `/app/cases/:id` | Queue filters/status/priority/origin/mine; claim, note, resolution/reasoning/assignment rules. Mounted Investigation/Evidence/Decision/Activity panels preserve unsent drafts; keyboard tab controls | CaseDetail tests including draft retention; browser claim/note/resolve; API role/validation tests |
| INV | Case Investigation panel | Start and poll supported investigation, deterministic fallback with explicit no-AI label, grounded findings, source refs/tool calls/budgets/history/failures | Workbench browser and unit tests, API investigations tests |
| EVID | Case Evidence & packets panel | Categorized supported upload/download, existing checklist, provenance and failure/permission handling | Browser upload/download and viewer checks, Workbench and API evidence tests |
| PACK | Case Evidence & packets panel | Generate/list/download PDF packets, checksum/version/snapshot/history, existing authorization | Workbench browser real PDF download; packet API tests |
| APPROVAL | Case Decision & approvals panel | Request/immutable snapshot; independent admin approve/reject; justification/audit; self-decision blocked; no payment execution | Workbench analyst→admin browser and unit tests; API approval guards |
| MODEL | `/app/model`; model publication and curve ledgers | Existing model card, datasets, calibration, threshold/PR/ROC metrics and limitations; no retraining or activation UI | Fixture-flow/operations browser, model accessibility checks, unchanged API/ML artifacts |
| OPS | `/app/operations`; operational register | Existing ADMIN diagnostics, provider/receiver/readiness/worker statuses, polling and error states. No fabricated healthy statuses | Operations admin/viewer browser and API operations tests |
| POLICY | `/app/policy`; assumption planner and comparison ledgers | Validation-only simulator inputs/reset, frozen benchmark, curves/confusion/capacity/cost assumptions, immutable save/submit/independent approve/reject. Serving thresholds unchanged | Functional policy browser compares before/after model thresholds; next-phase browser; policy API tests |
| MON | `/app/monitoring`; analytics and review context | Origin/window/capacity controls, scoped volume/risk/outcomes/drift/health and truthful insufficient-data warnings | Next-phase and operations browser, screenshots/axe, monitoring API tests |
| GRAPH | `/app/network`; relationship canvas plus record ledgers | Payer depth/origin/search/selection/deep links, merchant-scoped shared-payer evidence only, unsupported device/IP/card intelligence absent | Next-phase/operations browser and network API tests |
| REF | `/app/refunds?case=:id`; request and decision ledger | Case/amount validation, immutable request snapshot/history, independent approve/reject, existing execution guards; no financial execution control introduced | Functional browser request+independent approval; RefundsPage/API tests |
| DIS | `/app/disputes?case=:id`; preparation workbench | List/select, labeled demo, admin read-only sync, assign, checklist, grounded deterministic draft and PDF, explicit disabled external submission | Functional browser create/assign/draft/download; DisputesPage/next-phase/API tests |
| CHECK | `/app/checkout`; catalogue and order surface | Existing catalogue/quantity, order/capture/idempotency, fixture versus sandbox provenance; viewer restrictions; provider failure states | Fixture browser and CheckoutPage/API tests. Real PayPal not exercised |
| SET | `/app/settings`; integration/account diagnostics | Existing safe PayPal/AI status; admin paged audit; loading/error/denied state; no invented credential editor | Operations/fixture browser and API tests |
| DEMO | `/app/demo`; prepared scenario guide | DEMO-merchant viewer-safe scenario, investigation/packet links and read-only controls | Prepared-judge next-phase browser; judge API tests |
| STATIC | Portable hash build | Existing exported API-response snapshot and viewer permissions, no authentication server, write refusal and explicit static/synthetic banner | Static browser suite; separate exported snapshot and build |

## Reconstructed information architecture

The sidebar was replaced with horizontal primary navigation and a compact Explore menu. The real Command Center starts with an actionable priority queue, then separates origin-safe context from transaction/volume ledgers. The dossier prioritizes payment, recorded event story and a broad risk explanation. The case workbench separates investigation, evidence, decisions and activity into keyboard-operable panels. Policy assumptions precede comparison results; monitoring and relationships use distinct analytic and contextual sections. Checkout, dispute preparation, refunds and settings retain their own controls inside the new design. Original domain hooks and server checks are reused deliberately.

## Legacy presentation removal

Removed `src/preview/Preview.tsx`, its simulated `CommandCenter.tsx`, old preview providers/routes, old navigation wrapper and the preview directory. Promoted approved Story/Wallet/ReceiptMorph/fixtures into `src/features/experience`, scoped the approved CSS to `.sentinel-experience`, and removed merchant service querying from the public dossier. The experimental `/__v2-preview` path now renders the public 404 and its old entry chunks do not ship.

Replaced the production dark tokens, sidebar, boxed panel presentation, grid dark theme, login layout, dossier composition and case workbench layout. Removed unused legacy/experimental font dependencies (IBM Plex Sans, Inter, Space Grotesk, JetBrains Mono) and dead intermediate workbench CSS. Manrope, DM Sans and IBM Plex Mono are self-hosted. Retained business logic, supported controls, truthful status colors, grid and native provider branding. Historical reports and recovery history remain for audit; they are not application screens.

`git diff 4276a404 -- apps/api ml packages/contracts .github deploy` must remain empty. Database, migrations, training, provider/auth/CSRF/server authorization and deployment configuration are unchanged. The frontend session-cache correction preserves the same server login/logout/session contracts.

## Corrections found during verification

Sign-out previously completed on the server while a detached query observer retained the old screen. The session-cache correction now updates the live observer and removes private records; a regression test asserts both. Zod now uses its supported `jitless` setting so its optional dynamic-code probe does not raise a CSP violation; the existing server policy is unchanged. Dashboard/queue loading placeholders now have a named status role. Primary button text contrast and keyboard access to horizontally scrolling ledgers were corrected during the foundation checks. The mobile merchant/account bar uses separate readable rows.

## Verification limits and deployment verdict

The portable static build supports the original read-only snapshot areas (Command Center, transactions, recorded risk, cases and model). Operational writes and service-only diagnostics require the full API and are not simulated by the static adapter.

The review uses loopback PostgreSQL fixture databases, simulated checkout and deterministic summaries. Original seeded records are preserved; mutating browser tests operate on a cloned database. No real payment, real refund, external dispute submission, paid inference or remote publication is evidence from this phase. One backend real-AI integration test remains credential-gated and skipped.

Chromium desktop and mobile emulation are the browser evidence. Automated axe and keyboard checks do not constitute a complete accessibility certification or physical-device/screen-reader review. Cross-browser Safari/Firefox, genuine provider credentials/events, production workers/hosting and field performance remain separate verification work. Large ledgers intentionally scroll within keyboard-focusable regions on mobile; dense investigation and policy material remains long-form. The AG Grid route chunk still produces Vite's size advisory; route splitting keeps it out of the public homepage's initial request path.

Local functional reconstruction can be reviewed at Gate 2. Production deployment, pushing, merging, publishing and infrastructure changes remain unauthorized and have not been performed. Gate 1 approval does not imply Gate 2 approval.
