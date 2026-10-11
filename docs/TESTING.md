# Testing

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
