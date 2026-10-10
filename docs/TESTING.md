# Testing

## Run locally
```bash
# Backend (needs PostgreSQL with a sentinel_test database)
cd apps/api && .venv/bin/pytest && .venv/bin/ruff check app tests alembic && .venv/bin/mypy app
# Frontend
cd apps/web && npm run typecheck && npm run lint && npm test && npm run build
# E2E (API in fixture mode + Vite running, demo users seeded)
SENTINEL_E2E_ANALYST_PASSWORD=... npx playwright test
```

## Results recorded on 2026-10-10 (this container)
| Suite | Command | Result |
|---|---|---|
| Backend unit/integration (real PostgreSQL 16) | `pytest` | 39 passed |
| Backend lint / types | `ruff check`, `mypy --strict app` | clean / no issues in 47 files |
| Migrations | `alembic downgrade base && alembic upgrade head` | round-trip OK |
| Frontend types / lint | `tsc -b`, `eslint .` | clean |
| Frontend unit | `vitest run` | 12 passed (4 files) |
| Frontend build | `vite build` | OK (AG Grid chunk ~1.1 MB, lazy-loaded) |
| E2E + accessibility | `playwright test` (Chromium, 1440×900 and Pixel 7) | 4 passed; axe WCAG 2.0/2.1/2.2 A+AA: 0 violations on login, Command Center, checkout, transactions, detail, settings; no horizontal overflow |

## What the mocks do and do not prove
- `tests/paypal_mock.py` imitates documented PayPal responses to test our HTTP handling. It does **not** prove PayPal integration.
- The fixture gateway exercises the product flow offline; all its records are `SIMULATED`.
- A live sandbox integration test (`tests/integration/`) will be added and run once credentials exist; it is not part of this session's results.
