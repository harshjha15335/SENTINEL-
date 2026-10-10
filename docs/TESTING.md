# Testing

## Run locally
```bash
# Backend (needs PostgreSQL with a sentinel_test database)
cd apps/api && .venv/bin/pytest && .venv/bin/ruff check app tests alembic && .venv/bin/mypy app
# ML pipeline (needs `pip install -e "apps/api[dev,ml]"`)
PYTHONPATH=apps/api:ml apps/api/.venv/bin/pytest ml/tests
# Frontend
cd apps/web && npm run typecheck && npm run lint && npm test && npm run build
# E2E (API in fixture mode + Vite running, demo users seeded)
SENTINEL_E2E_ANALYST_PASSWORD=... npx playwright test
```

## Results recorded on 2026-10-10 (this container, session 2)
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
