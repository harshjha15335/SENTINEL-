# SENTINEL – project context for Claude Code

AI payment trust & recovery platform for PayPal merchants (PayPal AI Hackathon 2026, deadline
2026-11-12 12:00 PT). Decision support, not an autonomous payment authority.

## Layout
- `apps/api` FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL. Entry `app/main.py`.
- `apps/web` React 19 + Vite + TS strict + Tailwind v4 tokens (`src/styles/tokens.css`) + Radix + AG Grid Community.
- `packages/contracts` OpenAPI JSON + generated TS types. Regenerate with `scripts/gen-contracts.sh` after any API schema change.
- `docs/` requirements, decisions (`docs/decisions/`), status (`docs/IMPLEMENTATION_STATUS.md`).

## Commands
- ML: `PYTHONPATH=apps/api:ml apps/api/.venv/bin/python -m sentinel_ml.train_operational` (retrain), `PYTHONPATH=apps/api:ml apps/api/.venv/bin/pytest ml/tests`; demo data `python -m app.cli demo-load`.
- API: `cd apps/api && .venv/bin/pytest`, `.venv/bin/ruff check app tests alembic`, `.venv/bin/mypy app`, `.venv/bin/alembic upgrade head`, `.venv/bin/python -m app.cli seed`, `.venv/bin/uvicorn app.main:app --reload`.
- Web: `cd apps/web && npm run typecheck && npm run lint && npm test && npm run build`; `npx playwright test` with API + Vite running.

## Non-negotiable rules
- Provenance: every record carries `data_origin` (LIVE_SANDBOX, MERCHANT_PROVIDED, SYNTHETIC_DEMO, SIMULATED). Never present simulated or fixture output as PayPal-confirmed. Never mix origins in aggregates.
- PayPal: sandbox host only, no live mode. Client never sends amounts. Use `PayPal-Request-Id` for every mutating call. Business code depends on the `PayPalGateway` protocol.
- Webhooks: certificate signature verification on raw bytes; persist before acknowledging; idempotent by event id.
- AI/agents: read-only, merchant-scoped tools; no payment mutation; financial actions only via approval workflow executed by backend code.
- ML: past-only features, chronological splits, thresholds/calibration on validation only, never invent metrics.
- Security: roles enforced server-side; CSRF header on mutations; no secrets in the browser bundle or logs.
- Aaryan Pawar's Fraud Risk Manager (Razorpay hackathon, All Rights Reserved) is a benchmark only. Never copy its code or assets.

## Conventions
- Money: integer minor units + ISO currency. Timestamps: timezone-aware.
- Domain errors subclass `app.core.errors.DomainError`; API errors are `{error: {code, message, details, correlation_id}}`.
- Frontend: use tokens/utilities from `tokens.css`; tabular numerals (`tabular`) for amounts; every list needs loading, empty and error states; origin badge wherever a record is shown.
- Update `docs/IMPLEMENTATION_STATUS.md` with what actually ran, not what was planned.
