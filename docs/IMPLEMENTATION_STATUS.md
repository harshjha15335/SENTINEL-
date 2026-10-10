# Implementation Status

Last updated: 2026-10-10 (session 1). Update this file whenever real work lands.

## Implemented and tested
- Monorepo, pinned dependencies, ruff/mypy-strict/ESLint/TS-strict configuration.
- PostgreSQL schema + Alembic migration (merchants, users, user_sessions, products, transactions, payment_events, raw_payloads, audit_events); round-trip tested.
- FastAPI app: health, readiness, correlation ids, JSON logging with redaction, consistent errors, security headers, CORS.
- Auth: Argon2id login, server sessions, CSRF, RBAC, merchant isolation, login rate limit, audit events.
- PayPal gateway protocol; `SandboxPayPalGateway` (OAuth2, Orders create/capture/get, Payments get/refund, Disputes list/get) tested at HTTP level with mocks; `FixturePayPalGateway` (SIMULATED).
- Checkout service: server-side pricing, idempotent create, locked idempotent capture, amount verification, failure recording.
- Webhook intake: signature verification, durable storage, idempotency, reconciliation with status precedence, simulator isolation, retry worker.
- Transactions list/detail, dashboard summary split by origin, products, audit log endpoints.
- Shared contract: OpenAPI → `packages/contracts/openapi.ts`.
- Web: design tokens, app shell, login, Command Center, Transactions (AG Grid Community), transaction detail with event timeline, Sandbox Checkout (v6 PayPal buttons + labelled simulated path), Settings with PayPal status and audit log.
- Tests: 39 backend, 12 Vitest, 4 Playwright (desktop + mobile) with axe WCAG 2.2 AA.

## Implemented but not tested
- `app.workers.events` loop entry point (the processing function it calls is tested).
- PayPal v6 button rendering (needs a real sandbox client id).
- `refund_capture`, `get_capture`, `get_dispute` happy paths against PayPal.

## Blocked by credentials / permissions
- **First live sandbox order → approval → capture.** Needs `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET` and a sandbox buyer account.
- **Real webhook deliveries.** Needs a public HTTPS URL and `SENTINEL_PAYPAL_WEBHOOK_ID`.
- **Pushing code.** No GitHub repository exists for SENTINEL yet; the work is committed locally in an ephemeral container.
- Disputes API access depends on the sandbox account's permissions (not yet probed).

## Simulated only
- Fixture-gateway orders/captures (`SIMULATED`), used for offline development and e2e tests.

## In progress
- None outside this list.

## Not started
- Phase 2 remainder: cases, review queue.
- Phase 3: ML pipelines (Track A/B), risk assessments, SHAP.
- Phase 4: investigation agent, evidence upload, evidence packet, approvals.
- Phase 5: refund approval path, disputes workspace, graph analytics/explorer, policy lab.
- Phase 6: deployment, CSP, security review, demo video.
