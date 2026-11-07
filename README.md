Current external release review: [7 November 2026 status and owner actions](docs/PUBLIC_RELEASE_REVIEW.md). Supabase project is INACTIVE; public release remains blocked. Render and OpenAI/gpt-6.1-terra are selected proposals, not verified deployments or paid-use authorization.

Previous release verification: [Final release report](SENTINEL_FINAL_RELEASE_REPORT.md) and [deployment requirements](docs/FINAL_DEPLOYMENT.md), 6 November 2026. Local tests pass; genuine bridge/OAuth/AI and continuous public hosting remain blocked or unverified.

# SENTINEL · AI Payment Trust & Recovery

SENTINEL helps merchants who take payments with PayPal go from a suspicious payment to an
explainable, evidence-backed decision. It records PayPal sandbox payments and events, scores risk
with an explainable model, investigates cases with grounded, read-only AI tools, and routes any
financial action through human approval.

> **Development status (6 November 2026):** the recovered branch now includes a guarded
> refund ledger/executor, dispute preparation, validation-only Policy Lab, scoped risk
> monitoring, payer-reference network exploration and a refreshed private judge scenario.
> Financial execution is disabled by default; dispute submission is disabled. The existing
> investigation/evidence/approval system is extended, not replaced.
>
> The Python application is still local. The Supabase bridge is blocked by proxy CONNECT
> denial, sandbox OAuth returns `401 invalid_client`, and real AI remains unverified.
> Readiness correctly remains 503 while the required bridge is unhealthy. Fixture status
> never claims successful provider OAuth. Synthetic benchmark precision remains 28.2%.
>
> [Technical completion report](docs/NEXT_PHASE_REPORT.md) · [Setup](docs/NEXT_PHASE_SETUP.md) · [Runbook](docs/NEXT_PHASE_RUNBOOK.md) · [Judge guide](docs/NEXT_PHASE_DEMO.md)

## Historical demo launch options

Public `main` and images built from it do not contain the recovered local branch (`feature/reliability-next-phase`, not yet published). These links are not deployments of the Session 8 implementation. The old free Render blueprint is not a continuous hosting recommendation; use the review-only proposal and readiness checklist after authorization.

| Option | What you get | Needs |
|---|---|---|
| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/harshjha15335/SENTINEL-) | The full app with its database, in your browser, about 2 minutes after opening | A GitHub account. Codespaces usage counts against your account's quota. |
| [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/harshjha15335/SENTINEL-) | A public HTTPS URL that redeploys on every push to `main` | A Render account; verify current limits and pricing |
| `docker run ghcr.io/harshjha15335/sentinel:main` | The same image CI tests, published from `main` | Docker and a PostgreSQL URL |

The historical launch configurations are intended to run in **demo mode**:
- PayPal runs in fixture mode, so every payment it creates is labelled **Simulated**.
- The **Synthetic demo** scenario is loaded.
- Sign-in passwords are generated, never committed.
- Investigations produce the labelled deterministic summary unless `SENTINEL_AI_PROVIDER` and
  `SENTINEL_AI_API_KEY` are set.

Details, and how to switch a deployment to the PayPal sandbox, are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

Every record shows where it came from: **Live sandbox**, **Merchant provided**, **Synthetic demo**
or **Simulated**.

## Run it locally

Prerequisites: Python 3.12+, Node 22.22+ (24 recommended), PostgreSQL 16 (or Docker).

```bash
# 1. Database
docker compose up -d db            # or use a local PostgreSQL with databases sentinel + sentinel_test

# 2. API
cd apps/api
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp ../../.env.example .env          # fill in values; see below
.venv/bin/alembic upgrade head
SENTINEL_SEED_ADMIN_PASSWORD=... SENTINEL_SEED_ANALYST_PASSWORD=... SENTINEL_SEED_VIEWER_PASSWORD=... \
  .venv/bin/python -m app.cli seed
  .venv/bin/python -m app.cli demo-load   # optional: SYNTHETIC_DEMO history, scores and review cases
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m app.workers.events   # optional: webhook retry worker

# 3. Web
cd ../web && npm ci && npm run dev     # http://localhost:5173
```

Sign in as `admin@northwind.example`, `analyst@northwind.example` or `viewer@northwind.example`
with the passwords you seeded.

### PayPal sandbox vs offline mode
- `SENTINEL_PAYPAL_MODE=sandbox` (default) needs `SENTINEL_PAYPAL_CLIENT_ID` and
  `SENTINEL_PAYPAL_CLIENT_SECRET` from a PayPal Developer sandbox app. Checkout shows PayPal's
  buttons; approve with a sandbox buyer account. Webhooks need a public HTTPS URL and
  `SENTINEL_PAYPAL_WEBHOOK_ID`. Details: [`docs/PAYPAL_INTEGRATION.md`](docs/PAYPAL_INTEGRATION.md).
- `SENTINEL_PAYPAL_MODE=fixture` runs fully offline. Orders and captures are created locally and
  every one is labelled **Simulated**; nothing reaches PayPal.

### Investigation agent (optional)
Set `SENTINEL_AI_PROVIDER=anthropic` (or `openai`), `SENTINEL_AI_API_KEY` and optionally
`SENTINEL_AI_MODEL`. Without them, "Generate deterministic summary" produces a rule-based summary
from stored records, labelled "Deterministic summary — AI provider unavailable". Evidence files are
stored under `apps/api/var/storage` (or in PostgreSQL with `SENTINEL_STORAGE_BACKEND=database`).
Design: [`docs/AGENT_DESIGN.md`](docs/AGENT_DESIGN.md).

## Tests
See [`docs/TESTING.md`](docs/TESTING.md) for commands and the latest recorded results.

## Documentation
Product: [`PRODUCT_REQUIREMENTS`](docs/PRODUCT_REQUIREMENTS.md) · Architecture: [`ARCHITECTURE`](docs/ARCHITECTURE.md), [`DATABASE_SCHEMA`](docs/DATABASE_SCHEMA.md), [`decisions/`](docs/decisions) ·
Research: [`REFERENCE_ANALYSIS`](docs/REFERENCE_ANALYSIS.md), [`RESOURCE_DECISIONS`](docs/RESOURCE_DECISIONS.md), [`BASELINE_COMPARISON`](docs/BASELINE_COMPARISON.md) ·
[`SECURITY`](docs/SECURITY.md) · [`ML_METHODOLOGY`](docs/ML_METHODOLOGY.md) · [`AGENT_DESIGN`](docs/AGENT_DESIGN.md) · [`DEMO_SCRIPT`](docs/DEMO_SCRIPT.md)

## Licence
Apache-2.0. Third-party licences are listed in `docs/RESOURCE_DECISIONS.md`.
