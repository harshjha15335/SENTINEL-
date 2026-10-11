# SENTINEL · AI Payment Trust & Recovery

SENTINEL helps merchants who take payments with PayPal go from a suspicious payment to an
explainable, evidence-backed decision. It records genuine PayPal sandbox payments and events,
scores risk with an explainable model, will investigate with grounded AI tools, and routes any
financial action through human approval.

> **Status (2026-10-11):** Payments, verified webhooks, the transaction workspace, the risk model
> with SHAP explanations, and the review queue are built and tested. The risk model is trained on
> synthetic data only. No live PayPal sandbox payment has run yet because sandbox credentials
> have not been configured. The investigation agent, evidence, graph, disputes and policy lab
> are not built yet. See [`docs/IMPLEMENTATION_STATUS.md`](docs/IMPLEMENTATION_STATUS.md).

## Launch from GitHub

| Option | What you get | Needs |
|---|---|---|
| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/harshjha15335/SENTINEL-) | The full app with its database, in your browser, about 2 minutes after opening | A GitHub account. Codespaces usage counts against your account's quota. |
| [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/harshjha15335/SENTINEL-) | A public HTTPS URL that redeploys on every push to `main` | A free Render account |
| `docker run ghcr.io/harshjha15335/sentinel:main` | The same image CI tests, published from `main` | Docker and a PostgreSQL URL |

Every hosted option runs in **demo mode**:
- PayPal runs in fixture mode, so every payment it creates is labelled **Simulated**.
- The **Synthetic demo** scenario is loaded.
- Sign-in passwords are generated, never committed.

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

## Tests
See [`docs/TESTING.md`](docs/TESTING.md) for commands and the latest recorded results.

## Documentation
Product: [`PRODUCT_REQUIREMENTS`](docs/PRODUCT_REQUIREMENTS.md) · Architecture: [`ARCHITECTURE`](docs/ARCHITECTURE.md), [`DATABASE_SCHEMA`](docs/DATABASE_SCHEMA.md), [`decisions/`](docs/decisions) ·
Research: [`REFERENCE_ANALYSIS`](docs/REFERENCE_ANALYSIS.md), [`RESOURCE_DECISIONS`](docs/RESOURCE_DECISIONS.md), [`BASELINE_COMPARISON`](docs/BASELINE_COMPARISON.md) ·
[`SECURITY`](docs/SECURITY.md) · [`ML_METHODOLOGY`](docs/ML_METHODOLOGY.md) · [`AGENT_DESIGN`](docs/AGENT_DESIGN.md) · [`DEMO_SCRIPT`](docs/DEMO_SCRIPT.md)

## Licence
Apache-2.0. Third-party licences are listed in `docs/RESOURCE_DECISIONS.md`.
