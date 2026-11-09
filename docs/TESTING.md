# Testing

## Latest next-phase implementation — 6 November 2026

The new [technical report](NEXT_PHASE_REPORT.md) supersedes older feature-status and environment observations below. Guarded refunds, dispute preparation, validation-only Policy Lab, scoped monitoring/network views and a refreshed judge scenario are now implemented locally. Actual hosting, genuine PayPal/AI and remote bridge access remain separately blocked/unverified. See [setup](NEXT_PHASE_SETUP.md), [runbook](NEXT_PHASE_RUNBOOK.md), [architecture](NEXT_PHASE_ARCHITECTURE.md) and [demo](NEXT_PHASE_DEMO.md). Earlier dated inventories remain historical.

## Session 8 operational status — 22 October 2026

The current recovered branch adds supervised Supabase HTTP ingestion, durable scoring, exact-schema readiness, an administrator operations page and a private read-only judge scenario. The receiver is public; the Python application is still workspace-local. Certificate-host reachability now works; sandbox OAuth authentication failed. Real PayPal payments remain deliberately untested, and the real-AI test remains credential-gated. See [SESSION_8_REPORT.md](SESSION_8_REPORT.md), [HOSTING_READINESS.md](HOSTING_READINESS.md) and [PROVIDER_VERIFICATION.md](PROVIDER_VERIFICATION.md) for current evidence. Older dated results below are historical, not current deployment claims.

## Run locally
```bash
# Backend (needs PostgreSQL with a sentinel_test database)
cd apps/api && .venv/bin/pytest && .venv/bin/ruff check app tests alembic && .venv/bin/mypy app
# ML pipeline (needs `pip install -e "apps/api[dev,ml]"`)
PYTHONPATH=apps/api:ml apps/api/.venv/bin/pytest ml/tests
# Frontend
cd apps/web && npm run typecheck && npm run lint && npm test && npm run build
# E2E (API in fixture mode + Vite running, demo users seeded, demo-load run)
SENTINEL_E2E_ANALYST_PASSWORD=... SENTINEL_E2E_ADMIN_PASSWORD=... npx playwright test
# Provider-backed investigation test (skipped unless real credentials are supplied)
cd apps/api && SENTINEL_IT_AI_PROVIDER=anthropic SENTINEL_IT_AI_API_KEY=... .venv/bin/pytest tests/integration
```

## Results recorded on 2026-10-11 (this container, session 3)
| Suite | Command | Result |
|---|---|---|
| Backend (real PostgreSQL 16) | `pytest` | 103 passed, 1 skipped (provider-backed test: no AI credentials) |
| Backend lint / types | `ruff format --check`, `ruff check`, `mypy --strict app` | clean / no issues in 73 files |
| ML pipeline | `pytest ml/tests` | 7 passed; committed model artifact unchanged |
| Migrations | `alembic downgrade base && alembic upgrade head`, `alembic check` | round-trip OK, no drift |
| Frontend types / lint | `tsc -b`, `eslint .` | clean |
| Frontend unit | `vitest run` | 26 passed (8 files) |
| Frontend build | `vite build` | OK. Transactions chunk 1,161.5 kB → 744.0 kB (gzip 324.0 → 210.5 kB) after registering only the AG Grid modules used |
| E2E + accessibility | `playwright test` (Chromium, 1440×900 and Pixel 7) | 8 passed, including the Phase 4 workbench flow (deterministic summary → upload → packet → refund-intent request → admin approval → audit trail) with axe WCAG 2.2 AA = 0 violations and no horizontal overflow |

New backend tests (51): `test_investigations.py` (credentials/fallback, scripted AI runs,
read-only tool set, denied unknown tools, prompt injection, fabricated evidence/transaction/id
references, verbatim excerpts, cross-merchant evidence in tools, past-only payer history, timeout,
invalid output, budget, provider 401 classification, duplicate and concurrent starts, stale runs,
cross-merchant/invalid ids, roles/auth/CSRF, audit leakage), `test_evidence_packets.py` (valid PDF
and PNG, 7 invalid-file cases, active/encrypted PDFs, size limit, duplicates, unsafe paths,
download authorisation, database storage, packet content and access), `test_approvals.py` (refund
intent never executes, separation of duties, reject/duplicate pending, packet snapshot,
viewer/cross-merchant, non-captured refunds, concurrent decisions, DB immutability triggers).

**Scripted models prove our tools, validation and persistence, not real model behaviour.**
Provider-backed verification is blocked until AI credentials are configured.

## Results recorded on 2026-10-10 (session 2)
| Suite | Command | Result |
|---|---|---|
| Backend unit/integration (real PostgreSQL 16) | `pytest` | 52 passed |
| Backend lint / types | `ruff format --check`, `ruff check`, `mypy --strict app` | clean / no issues in 58 files |
| ML pipeline | `pytest ml/tests` | 7 passed (leakage, split order, parity with SHAP, reproducibility) |
| Migrations | `alembic downgrade base && alembic upgrade head` | round-trip OK |
| Frontend types / lint | `tsc -b`, `eslint .` | clean |
| Frontend unit | `vitest run` | 16 passed (6 files) |
| Frontend build | `vite build` | OK (AG Grid chunk ~1.1 MB, lazy-loaded) |
| E2E + accessibility | `playwright test` (Chromium, 1440×900 and Pixel 7) | 6 passed. axe WCAG 2.0/2.1/2.2 A+AA reported 0 violations on 9 screens: login, Command Center, checkout, transactions, transaction detail, settings, review queue, case detail and risk model. No horizontal overflow. |

The E2E run uses the dev database after `python -m app.cli demo-load`, so the review queue has cases.

## What the mocks do and do not prove
- `tests/paypal_mock.py` imitates documented PayPal responses to test our HTTP handling. It does **not** prove PayPal integration.
- The fixture gateway exercises the product flow offline; all its records are `SIMULATED`.
- A live sandbox integration test (`tests/integration/`) will be added and run once credentials exist; it is not part of this session's results.

## Session 8 validation

Current source passes the full backend suite (134 passed, 1 real-AI skip), including transport-loss replay coverage, unchanged ML (7), frontend (29), browser desktop/mobile (12), Deno receiver (11) and explicitly configured Supabase SQL/deployment checks (12). An initial Supabase run omitted the isolated SQL URL and skipped eight tests; the corrected run set `SENTINEL_SUPABASE_TEST_DATABASE_URL` to the dedicated local `sentinel_supabase_check` database and passed all twelve. Skips are not counted as SQL validation.

The new backend coverage checks exact migration mismatch, stale/future/degraded heartbeats, origin/tenant scoping, operator-only inbox snapshots, idle last-success preservation, hosted security configuration, idempotent judge provisioning and viewer read-only access. The transport-loss regression lets FastAPI commit the event, drops its HTTP response, then verifies replay creates only one event/job/case.

Browser operations/judge checks use actual API data, desktop/mobile viewports and axe. Read the prepared fixture document, download private packets and verify server authorization; never publish the passwords. A full supervisor restart retained sessions and identical evidence/packet SHA-256. A fresh local PostgreSQL dump restored 18,108 transaction rows and all fourteen stored blobs into a separate disposable database. These are local tests, not hosted backup or genuine provider claims.

The hosted SIMULATED fixture run used an isolated integration database, generated one HIGH case, and exercised duplicate delivery, expired claim, API outage, stale acknowledgement, out-of-order status and deliberate invalid HMAC. Provider calls: zero. Its rows are kept labelled, not removed or relabelled as real payments. The ordinary production bridge never claims SIMULATED receipts.
