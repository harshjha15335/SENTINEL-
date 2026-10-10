# Implementation Status

Last updated: 2026-10-10 (session 2). Update this file whenever real work lands.

## Implemented and tested

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
| Backend | 52 passed |
| ML | 7 passed |
| Vitest | 16 passed |
| Playwright (desktop + mobile) | 6 passed, with axe WCAG 2.2 AA on 9 screens |

## Implemented but not tested
- The `app.workers.events` loop entry point. The processing function it calls is tested.
- PayPal v6 button rendering, which needs a real sandbox client id.
- `refund_capture`, `get_capture` and `get_dispute` happy paths against PayPal.

## Blocked by credentials / permissions
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
- **Review capacity.** The test-window flag rate (9.4%) exceeds the 8% capacity the threshold was tuned for on validation. This is documented on the Risk Model page.
- **Bundle size.** The AG Grid chunk is about 1.1 MB, lazy-loaded. Trimming it to the modules actually used is a follow-up.

## Not started
- **Phase 4:** investigation agent (PydanticAI, read-only tools), evidence upload, evidence packet, approvals.
- **Phase 5:**
  - refund approval path
  - disputes workspace
  - graph analytics and explorer
  - policy lab
- **Phase 6:** deployment, CSP, security review, demo video.
