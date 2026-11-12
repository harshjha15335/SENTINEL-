> Latest release authorization (12 November 2026): owner-verified Blueprint,
> webhook and empty-Staging checks are accepted; remaining uninspected integrations
> are acknowledged residual risk. Earlier blanket H02 publication blocks below are
> historical and superseded by docs/remediation/2026-11-12/owner-release-evidence.md.
> Current CI/Docker/source-preservation and billing/plan gates still apply.

## Autonomous release follow-up — 12 November 2026

The latest owner instruction conditionally authorizes publication, reviewed merges
and Render-only staging within verified eligible credits. Earlier blanket pending-
approval statements below are historical; H02, exact-source Docker/CI and billing/
plan prerequisites remain mandatory. No publication, merge or provisioning occurred.

Fixed a confirmed defect in the prepared container acceptance runner: its local
`http` function shadowed the module used for HTTP connections and error handling.
The runner now uses explicitly imported HTTPConnection/HTTPException and a tested
loopback probe; four new regression cases run before Docker in the CI gate. Existing
application/runtime source, UI, models, contracts, dependencies and migration revisions
are unchanged by this follow-up. Full regression rerun evidence is recorded in the
external autonomous-release report. Full Docker acceptance remains unexecuted because
local capacity is insufficient and H02 prevents safe publication to run GitHub CI.

See docs/remediation/2026-11-12/autonomous-release.md for the precise owner evidence,
updated authorization, same-Blueprint sequence and budget/stop prerequisites.

# Scoped Render TLS approval and merge candidate — 12 November 2026 (Asia/Calcutta)

Owner approved only synthetic Render staging's encrypted-only TLS policy; no publication, merge, provisioning or spending approval. Starting 268adacaa0958a7bb5df6cdc576ee2d8e77bbfae is preserved at backup/render-tls-268adac. Applied/hardened policy: default hosted verify-full unchanged; exception requires approved staging/project/workspace tuple, exact reviewed internal host/user/database, secure fixture/no-provider profile, no connection redirects or ambient libpq overrides. Effective Alembic URLs are validated and connection identity/TLS explicitly pinned. Configuration errors suppress input secrets. Actual resource identity still requires owner review when resources exist; require does not authenticate the server certificate.

Fresh full matrix **597 passed, one live-AI skipped**: 445 API, 53 frontend, 7 ML, 34 auxiliary, 34 operational browser, 24 static browser; 63 new security cases. Lint/types/format, three builds, contracts, disposable migrations/schema, security/keyboard/production isolation pass; 51 visual checks report no defects. Approved UI/model/revision/financial-control sources unchanged. Local Docker remains capacity-blocked (~8 GB filesystem, <0.25 GB free, VFS, no build cache); no unrelated files/worktrees/recovery backups deleted. Prepared build-only GitHub container acceptance with read-only token, exact SHA/clean tree, generated credentials, isolated internal fixtures, mandatory TLS/default verification checks, migrations/worker/UI/restart evidence, no deployment/registry push. Workflow is NOT executed. Three Blueprint schemas/manual controls pass; 2 GB app + 1 GB DB proposal stays $44.30/month base. No push, PR action, merge, Render creation/application, genuine provider call, paid AI or credits spent. H02, fresh Docker CI, actual host/proxy/account/quote review and separate approvals remain. See deploy/render-staging.md and docs/remediation/2026-11-12/tls-approval.md.

# Render staging compatibility remediation — 12 November 2026 (Asia/Calcutta)

Local-only correction on fix/sentinel-v2-acceptance-blockers, preserving checkpoint 8993816840192e259cedc2e02809d455328a85ff at backup/render-staging-8993816. Mode-aware readiness now permits intentionally unconfigured fixture staging while requiring genuine pipeline/schema/database health; configured/sandbox bridges remain mandatory and incomplete settings fail closed. Supervisor restart states and graceful pipeline STOPPED heartbeat are truthful. Strict database verify-full remains active. A narrow encrypted-only internal Render policy is an INERT approval-pending patch, not applied runtime code.

Fresh full matrix: **534 passed, 1 credential-gated live-AI skipped** (382 API, 53 frontend, 7 ML, 34 auxiliary, 34 operational browser, 24 static browser), 26 new cases over 508. Backend/frontend lint/types and formatting, ML checks, three frontend builds, contracts, disposable schema/migrations, security/keyboard/production isolation pass; 51 visual checks have no reported layout/accessibility/page defects. Actual local hosted-profile entrypoint, strict TLS 1.3 DB sessions, crash-induced 503/recovery, graceful STOPPED and restart pass. Real queued-job owner-death handoff yields one assessment/one attempt after duplicate enqueue.

Database sizing: capped 256 MiB/0.1 CPU stayed functional but p95 5.80 s failed the pre-set 2 s four-reader workload target; capped 1 GiB/0.5 CPU passed at 0.74 s. Keep 1 GB PostgreSQL and 2 GB web: published base $44.30/month, actual fees/credits unverified. Original local test-server limits/TLS settings and all databases were preserved/restored. Full Dockerfile build and container startup remain BLOCKED by local VFS disk exhaustion; failed attempts retained, not presented as passes. Approved UI, models, financial controls, migrations, contracts, Dockerfile and dependency pins are unchanged. Root/staging manifests are canonical mirrors; database-only first phase belongs to the SAME future manual Blueprint. No push, PR update, merge, Render creation/application/resource change, genuine provider call, paid AI or credit spend. H02, TLS security decision, fresh Docker evidence and explicit approvals remain open. See [full staging handoff](../deploy/render-staging.md).

# Render-only staging Blueprint preparation — 11 November 2026

Owner-verified Sentinel / My Workspace / Staging has 0 services, 0 environment groups and no deployed resources; this does not prove no Blueprint or external binding. Root `render.yaml` now uses `autoDeployTrigger: 'off'` and disabled previews. New review-only `deploy/render-staging.yaml` proposes the unchanged FastAPI/React Docker application and PostgreSQL 16 for the existing project; Blueprint Auto Sync must separately be false in account metadata. Current published base estimate is $44.30/month (2 GB web, 1 GB PostgreSQL, 1 GB DB disk), excluding extras and workspace fees; actual billing/credits are not verified.

Verified: both manifests pass current public JSON Schema, two existing Render contract tests pass, actual Settings accepts fixture/none flags, migration target matches the source graph, and an offline no-network readiness probe fails closed without the required Supabase bridge. Also identified a hosting incompatibility: internal Render PostgreSQL TLS does not support the application's required verify-full mode. These are unresolved application compatibility blockers, not successful hosted acceptance. No backend/UI/models/dependencies were changed; full 508-test suite was not rerun. Render CLI is absent; no platform-side validation. Historical continuous proposal remains intentionally unresolved. See [staging handoff](../deploy/render-staging.md) for findings, evidence limits, H02 checklist, exact approval gates, budget and deployment procedure. No push, merge, provisioning, deployment, hosting mutation or credits spent.

# Local acceptance-blocker remediation — 11 November 2026

Local branch `fix/sentinel-v2-acceptance-blockers` corrects S01–S04 and local H01 handoff. Final local verification: **508 passed, 1 live-AI skipped** (356 API, 53 frontend, 7 ML, 34 auxiliary, 58 browser). Formatting/lint/typing, production/portable/Pages builds and production isolation passed. Earlier failed/interrupted runs and frontend timeout instability are retained in external evidence. No tests/timeouts/Axe rules weakened.

Approved V2 presentation, models/migrations and payment/scoring/investigation semantics remain preserved outside the scoped fixes. H02 remains a merge blocker; H01 hosted rollout and H03 hosting approval/acceptance remain open. PR #2/main unchanged. No push, merge, deployment or paid/provider execution. See [remediation handoff](remediation/2026-11-11/README.md), hosting proposal and owner verification checklist. Exact final SHA is in the external delivery report.

# Implementation Status

## SENTINEL UI/implementation integration — 11 November 2026

The isolated `integration/sentinel-v2-antigravity-20261111` branch combines approved UI `dd5e790` and GitHub main `482985f`, preserving both histories. [Draft PR #2](https://github.com/harshjha15335/SENTINEL-/pull/2) and [integration audit](integration/2026-11-11/README.md) record reconciliation and exact evidence. Executed: 302 API passed/1 credential-gated live-AI skipped, 49 frontend, 7 ML, 34 auxiliary, 24 static browser and 26 operational browser passed; formatting/lint/types, three builds, contracts and production isolation passed. Frontend/runtime backend/model artifacts remain identical to their respective sources; static payload matches Gate 2C. No main/source/tag rewrite, hosted data mutation or deployment. READY FOR REVIEW; DESIGN APPROVAL: APPROVED; DEPLOYMENT APPROVAL: PENDING.

## SENTINEL Gate 2C loading stability — 10 November 2026

Targeted frontend correction complete. All 18 controlled primary-page samples have CLS 0; 18 throttled samples have maximum CLS 0.001552. Gate 2B transaction maximum was 0.575 mobile. Preserved all 9,064 transactions, 1,824 assessments and 179 cases; no backend/model/contracts or approved homepage changes. Verified 49 frontend unit tests, 24 static/CSP/loading browser tests, 26 operational browser tests, 10 snapshot tests, typing, lint, all three builds and production isolation. See [Gate 2C report](sentinel-v2/17-gate2c-loading-stability.md) and the delivery evidence for detailed measurements. Secondary mobile case-detail CLS remains 0.119 in one exploratory sample; throttled full-data readiness reaches about 8.5s. No field-performance or actual-host claim. DESIGN APPROVAL: APPROVED. DEPLOYMENT APPROVAL: PENDING. No push, merge, resources or deployment.

## SENTINEL Gate 2B static host preparation — 10 November 2026

Cloudflare Pages preparation is isolated under [hosting/cloudflare-pages](../hosting/cloudflare-pages/README.md). The approved Gate 2A portable payload remains byte-for-byte unchanged; only reviewed `_headers` and a physical-path recovery `404.html` are added. Snapshot revalidation confirms 9,064 transactions, 1,824 assessments, 179 cases and zero unresolved references. No backend, hosting resources, sharing settings, pushes, merges or deployments changed. DESIGN APPROVAL: APPROVED. DEPLOYMENT APPROVAL: PENDING.

Executed locally: type checking/lint, 10 snapshot regression tests, 18 desktop/mobile Chromium tests with enforced CSP, and 118 encoding/decoded-hash/ETag checks covering 59 served files. The browser checks include actual wallet scroll/reverse, reduced motion, keyboard, search, recorded risk/cases/model, read-only restrictions and intentional inline-script rejection. Cloudflare's current official documentation was reviewed from its pinned GitHub source because the documentation domain is blocked in this executor. Provider acceptance/HTTPS/cache behavior at an actual hostname remains untested.

Lab performance: three cold-browser samples per scenario/device, warm loopback HTTPS server, no network throttling; mobile uses viewport emulation plus simulated 4× CPU slowdown. Median ready times: homepage 1.29s desktop / 2.22s mobile; transactions 2.10s / 3.93s; recorded risk 1.51s / 3.86s. Homepage observed CLS was zero, but transaction-grid maximum observed CLS reached 0.315 desktop / 0.575 mobile; recorded risk reached 0.082 / 0.240. These are documented performance concerns, not passing field Core Web Vitals. Preserve the verified application; accept or address record-view layout/loading concerns deliberately before publication. Actual-host performance and wider browser/device testing remain pending.

## SENTINEL V2 frontend reconstruction — 10 November 2026

Gate 1 was explicitly approved. The complete operational frontend and public Follow the Money homepage have been reconstructed locally; `/app` is the authenticated entry, with compatible legacy deep links. See [Phase 2 report](sentinel-v2/13-phase2-reconstruction.md). Backend, ML, database and API contracts remain unchanged. Final delivery evidence records test counts and review limits. Deployment/Gate 2 remains PENDING; no push, merge or deployment occurred.

## Latest next-phase implementation — 6 November 2026

The new [technical report](NEXT_PHASE_REPORT.md) supersedes older feature-status and environment observations below. Guarded refunds, dispute preparation, validation-only Policy Lab, scoped monitoring/network views and a refreshed judge scenario are now implemented locally. Actual hosting, genuine PayPal/AI and remote bridge access remain separately blocked/unverified. See [setup](NEXT_PHASE_SETUP.md), [runbook](NEXT_PHASE_RUNBOOK.md), [architecture](NEXT_PHASE_ARCHITECTURE.md) and [demo](NEXT_PHASE_DEMO.md). Earlier dated inventories remain historical.

## Session 8 operational status — 22 October 2026

The current recovered branch adds supervised Supabase HTTP ingestion, durable scoring, exact-schema readiness, an administrator operations page and a private read-only judge scenario. The receiver is public; the Python application is still workspace-local. Certificate-host reachability now works; sandbox OAuth authentication failed. Real PayPal payments remain deliberately untested, and the real-AI test remains credential-gated. See [SESSION_8_REPORT.md](SESSION_8_REPORT.md), [HOSTING_READINESS.md](HOSTING_READINESS.md) and [PROVIDER_VERIFICATION.md](PROVIDER_VERIFICATION.md) for current evidence. Older dated results below are historical, not current deployment claims.

Historical implementation baseline: 2026-10-11 (session 3). Current Session 8 results are above and in SESSION_8_REPORT.md.

## Historical Phase 4 inventory

### Foundations
- Monorepo with pinned dependencies and ruff / mypy-strict / ESLint / TS-strict configuration.
- CI on GitHub runs four jobs: api, ml, contracts and web.
- PostgreSQL schema with two Alembic migrations, round-trip tested.
- **FastAPI app:**
  - health and readiness endpoints, correlation ids
  - JSON logging with redaction, consistent errors
  - security headers and CORS
- **Auth:**
  - Argon2id login, server sessions, CSRF
  - RBAC, merchant isolation, login rate limit
  - audit events

### PayPal and payments
- **PayPal gateway protocol.**
  - `SandboxPayPalGateway` is tested at the HTTP level with mocks.
  - `FixturePayPalGateway` produces SIMULATED records.
- **Checkout:**
  - server-side pricing
  - idempotent create
  - locked, idempotent capture with amount verification
- **Webhook intake:**
  - signature verification and durable storage
  - idempotency and reconciliation with status precedence
  - simulator isolation and a retry worker
  - refund events now record `refunded_at`

### Risk engine (Phase 3, Track B)
- Seeded synthetic scenario (SYNTHETIC_DEMO).
- Past-only features shared by training and serving.
- Rules baseline vs logistic regression vs XGBoost.
- Calibration and a cost-based threshold, both set on validation, then one held-out test evaluation.
- Results are in `docs/ML_METHODOLOGY.md`.
- **Serving:**
  - pickle-free artifact with digest check
  - scoring after capture, plus manual re-scoring
  - exact TreeSHAP explanations
  - shadow-mode policy decisions
  - per-assessment limitations

### Review cases (Phase 2)
- **Opened** automatically for HIGH assessments, or manually.
- **Analyst actions:** claim, notes, resolve (Confirmed adverse / Legitimate / Inconclusive).
- **Rules:**
  - at most one open case per payment
  - every action audited
  - note text is kept out of the audit log
  - resolving never moves money
- **Queue:** sorted by priority, due date and score.

### Investigation, evidence and approvals (Phase 4)
- **Investigation runs** (`investigation_runs`): PydanticAI agent with 11 read-only, case-bound
  tools (3 report "not available until Phase 5"), typed findings, server-side grounding checks,
  budgets and timeouts, one active run per case, failure categories, full history kept.
- **Deterministic fallback** labelled "Deterministic summary — AI provider unavailable"; this is
  what runs in this environment because no AI credentials exist.
- **Evidence** (`evidence_artifacts`): PDF/PNG/JPEG upload with type, extension, signature, size,
  active-content and encryption checks, SHA-256, pypdf text extraction, contained local or
  database storage, authorised downloads, audit events.
- **Evidence packets** (`evidence_packets`): ReportLab PDF with case, provenance, chronology,
  risk, evidence inventory, excerpts, labelled findings, missing information and review status.
- **Approvals** (`approval_requests`, `approval_decisions`, `action_executions`): manual review,
  internal packet approval and refund intent; immutable snapshots, role and separation-of-duties
  checks, one decision per request, refund approvals never call PayPal.
- **Investigation Workbench** on the case page: payment, risk + SHAP, run controls and state,
  findings with cited sources, tool trace, run history, evidence inventory and upload, checklist,
  packet export, approvals, full activity timeline.
- **Review-capacity warning** on the Risk Model page and review queue, from recorded metadata
  (test flag rate 9.4% vs 8% validation capacity). Threshold not re-tuned; policy stays shadow.
- **AG Grid** registers only the modules it uses: transactions chunk 1,161.5 kB → 744.0 kB.

### Demo data, contract and web app
- `python -m app.cli demo-load` loads 9,051 SYNTHETIC_DEMO payments and scores the 1,811 held-out ones. Its 170 HIGH results match the offline evaluation.
- Shared contract: OpenAPI → `packages/contracts/openapi.ts`.
- **Web screens:**
  - login and Command Center (now with risk and review per origin)
  - Transactions grid with a risk column
  - Transaction detail with a risk panel (score, SHAP drivers, shadow policy, limitations, re-score) and case status
  - Review Queue and Case detail (claim, notes, resolve)
  - Risk Model card
  - Sandbox Checkout and Settings

### Tests
| Suite | Result |
|---|---|
| Backend | 111 passed, 1 skipped (provider-backed AI test: no credentials) |
| ML | 7 passed |
| Vitest | 26 passed |
| Playwright (desktop + mobile) | 8 passed, with axe WCAG 2.2 AA on 9 screens plus the workbench, both against Vite and against the built app served by the API with its CSP (no violations) |

### Deployment (session 3)
- **Single container:** the root `Dockerfile` serves the API and the web app from one origin, with a CSP on HTML responses.
- **Start-up:** migrate, seed, then load the demo data once.
- **Locally verified:** the image was built and run. The Playwright suite passed against it (6 tests, no CSP violations) and so did the CI smoke script.
- **Codespaces:** the `.devcontainer/` setup and start scripts were verified on a clean copy (6 e2e tests passed).
- **Render:** `render.yaml` Blueprint.
- **GitHub Actions:** the `Image` workflow builds, smoke-tests and publishes to GHCR.
- **GitHub Pages (read-only static demo):** the `Pages` workflow exports real API responses from the synthetic demo loader, builds the web app in static mode, runs the static e2e suite and deploys. Locally verified: the export (9,051 transactions, 1,811 assessments, 170 cases) and 6 Playwright tests against a Pages-like server, desktop and mobile, with axe checks.
- **Evidence storage:** the image sets `SENTINEL_STORAGE_BACKEND=database`, because container disks are ephemeral and the runtime user cannot write to the app directory. The image itself was not rebuilt after this change.
- See `docs/DEPLOYMENT.md`.

## Implemented but not tested
- The `app.workers.events` loop entry point. The processing function it calls is tested.
- PayPal v6 button rendering, which needs a real sandbox client id.
- **Hosted deploys:**
  - The Render deploy needs Harsh's Render account.
  - A real Codespace has not been created yet. Only its scripts were run here.
- `refund_capture`, `get_capture` and `get_dispute` happy paths against PayPal.

## Blocked by credentials / permissions
- **Provider-backed AI investigation.** Implemented and tested with scripted models only.
  Completion criterion 4 ("launch an actual tool-based AI investigation with configured
  credentials") is **blocked**: needs `SENTINEL_AI_PROVIDER` + `SENTINEL_AI_API_KEY` (and
  `SENTINEL_IT_AI_*` to run `tests/integration`).
- **First live sandbox order → approval → capture.** Needs:
  - `SENTINEL_PAYPAL_CLIENT_ID`
  - `SENTINEL_PAYPAL_CLIENT_SECRET`
  - a sandbox buyer account
- **Real webhook deliveries.** Needs a public HTTPS URL and `SENTINEL_PAYPAL_WEBHOOK_ID`.
- **Track A (IEEE-CIS) benchmark.** Needs Kaggle access and acceptance of the competition rules.
- **Disputes API access.** Depends on the sandbox account's permissions, which have not been probed yet.

## Simulated or synthetic only
- **Fixture-gateway orders and captures** (SIMULATED), used for offline development and e2e tests.
- **The risk model.** It is trained and evaluated on SYNTHETIC_DEMO data only.
  - Scores on sandbox or simulated payments demonstrate the pipeline.
  - Every such assessment carries that limitation.
- **`disputed_at`.** It is set only by the synthetic loader so far. Dispute webhooks will set it in Phase 5.

## Known gaps
- **Review capacity.** The test-window flag rate (9.4%) exceeds the 8% validation capacity. Now
  surfaced as a warning on the Risk Model page and review queue; deliberately not re-tuned.
- **Bundle size.** The transactions chunk is still 744 kB because AG Grid core is most of it.
- **Investigations** run as in-process background tasks; a restart abandons a running run (the
  stale-run rule recovers it). No OCR for images or scanned PDFs; no antivirus scanning.
- **Evidence packets** are internal documents. Submitting evidence to PayPal disputes is Phase 5.

## Not started
- **Phase 5:**
  - executing approved refunds (approval and intent recording exist)
  - disputes workspace
  - graph analytics and explorer
  - policy lab
- **Phase 6:** deployment, CSP, security review, demo video.

### Local V2 creative reset — Follow the Money (2026-11-09)

The isolated development preview is replaced with an original wallet/money narrative and warm ivory/electric-purple identity, per explicit rejection of the reel design. New horizontal navigation, chronological payment casefile, read-only transaction explorer and clearly labeled simulated Command Center composition are scoped to the preview. Existing operational screens, backend, auth and production routes remain intact. See `docs/sentinel-v2/09-money-trail-reset.md` and the delivered test report for verification; prior reel captures are historical. Design and deployment approval remain PENDING. No broad Phase 2 migration, push, merge or deployment.

Follow the Money validation: 43 frontend tests; 262 backend passed and one skipped; 19 Chromium tests plus three targeted transition rechecks; typing/lint/builds/production isolation and additional desktop/mobile accessibility audits passed. See `docs/sentinel-v2/10-money-trail-qa.md` for execution details and limits.

### Final Gate 1 visual polish — 10 November 2026 (Asia/Calcutta)

Retained the preferred Follow the Money direction and isolated scope. Wallet folds/pockets/bill layers, six staggered curled notes, native receipt-to-header transformation (no scaled workspace text), larger small labels, SVG navigation icons and explicit simulated/authenticated entry are implemented. Command Center remains a labeled simulated composition prototype; Phase 2 has not begun. Verification: 43 frontend passed; 262 backend passed, one provider skip; 20 Chromium passed plus the affected morph recheck; typing/lint, normal/static builds and production isolation passed. See `docs/sentinel-v2/11-gate1-polish.md` and the new approval ZIP for exact SHA, captures and limitations. Both approvals remain PENDING. No backend, auth, contract, infrastructure or legacy-screen source changes; no push, merge or deployment.
