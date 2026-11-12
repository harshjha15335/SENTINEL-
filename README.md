# SENTINEL

**Follow the money. Explain the risk. Keep humans in control.**

An explainable payment-risk investigation and recovery-control platform built for the **PayPal AI Hackathon**. SENTINEL connects PayPal Sandbox payment events to XGBoost risk scoring, evidence-grounded Gemini investigations, human approvals, and operational analytics.

[![CI](https://github.com/harshjha15335/SENTINEL-/actions/workflows/ci.yml/badge.svg)](https://github.com/harshjha15335/SENTINEL-/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)
![React](https://img.shields.io/badge/React-TypeScript-149ECA)
![PayPal](https://img.shields.io/badge/PayPal-Sandbox_only-003087)
![License](https://img.shields.io/badge/License-Apache--2.0-blue)

**[Live staging website](https://sentinel-v2-staging.onrender.com/)** · **[One-click judge demo](https://sentinel-v2-staging.onrender.com/login)** · **[Public payment dossier](https://sentinel-v2-staging.onrender.com/demo-payment)** · **[Source code](https://github.com/harshjha15335/SENTINEL-)**

> **Scope:** This is a hosted, synthetic-data-focused **staging and hackathon demonstration**, not a production fraud decisioning service. PayPal integrations use **Sandbox only**; no real-money payment or refund execution is enabled. The model was trained and evaluated on generated data, not validated against real merchant losses.

## Why SENTINEL?

Fraud dashboards can show a risk score without explaining what an investigator should do next. SENTINEL connects the whole review process:

1. **Observe** a PayPal Sandbox payment or a clearly labelled simulated/synthetic record.
2. **Assess** its risk with a versioned XGBoost model, calibrated bands, and TreeSHAP explanations.
3. **Investigate** flagged cases with a read-only, tool-using Gemini agent that cites the actual case records it read.
4. **Collect evidence** and generate a private PDF case packet.
5. **Escalate to a person** for review, approvals, disputes, and guarded refund preparation.
6. **Improve decisions** with shadow Policy Lab simulations, monitoring, and relationship exploration.

Risk scoring does **not** block payments, and an AI recommendation does **not** execute a financial action.

## Try the demo

| Experience | Link | What to expect |
| --- | --- | --- |
| Cinematic public homepage | [Follow the Money](https://sentinel-v2-staging.onrender.com/) | Scroll-driven payment story and entry points |
| Public simulated payment | [Payment dossier](https://sentinel-v2-staging.onrender.com/demo-payment) | No sign-in or provider request; illustrative payments |
| One-click judge access | [Enter from login](https://sentinel-v2-staging.onrender.com/login) | Passwordless, time-limited **VIEWER** session in an isolated demo merchant |
| Authenticated operations | [Merchant sign-in](https://sentinel-v2-staging.onrender.com/login) | Analyst/admin accounts can demonstrate authorized workflows |

The **judge workspace contains synthetic records and a prebuilt deterministic investigation**. Its viewer cannot initiate new AI runs, upload evidence, approve decisions, check out, or request refunds. A **separate authenticated analyst session** is required to show the genuinely model-generated Gemini investigation workflow.

### Suggested judge walkthrough

Start at the homepage, select **One-click judge demo**, then follow the **Demo guide**. Open a payment's risk explanation, read the prepared investigation with citations, inspect its illustrative evidence and PDF packet, and explore Policy Lab, Risk Monitoring, and the payer relationship graph. Use an authorized analyst/admin account only for actions such as launching a new Gemini run or reviewing approvals.

## Product features

| Area | Capabilities |
| --- | --- |
| **Command Center** | Payment volumes and states, origin-separated risk bands, recent transactions, urgent review queue |
| **Transactions & risk** | Search/filter/sort payments; PayPal order/capture references; event timeline; calibrated LOW/MEDIUM/HIGH risk; exact TreeSHAP contributions |
| **Investigations** | Case triage and deadlines, Gemini-powered read-only tools, deterministic fallback, cited verified facts, risk/counter-indicators, missing evidence, run history and tool traces |
| **Evidence & recovery** | Private PDF/PNG/JPEG evidence, upload metadata and checksums, evidence checklist, downloadable case packets, notes and activity audit |
| **Human approvals** | Claim/resolve review cases, independently review actions, prevent self-approval, preserve decision and execution states separately |
| **Refund review** | Full/partial refund request preparation, independent approval, guarded ledger and reconciliation; financial execution off |
| **Dispute Copilot** | Dispute context, evidence gaps, grounded response drafts, downloadable private draft PDFs; external submission off |
| **Policy Lab** | Shadow threshold/cost/capacity simulations, baseline comparisons, confusion matrix, ROC/PR, calibration and financial-impact assumptions |
| **Risk Monitoring** | Origin/time-window metrics, score distributions, shifts, missingness, case volumes, review capacity and outcomes |
| **Relationship Explorer** | Merchant-scoped payer/payment/case network, provenance-backed connections and risk/time filters |
| **Sandbox Checkout** | Merchant-priced catalogue, PayPal Sandbox buyer approval and capture, idempotency and reconciliation |
| **Operations & integrations** | PayPal OAuth status, Supabase webhook inbox, worker heartbeat/readiness, reconciliation/scoring queues, role-based settings and audit log |
| **Public experience** | Cinematic landing page, simulated interactive payment dossier, secure one-click read-only judge demo |

## Risk model and evaluation

The **operational model is synthetic-trained**. Its dataset has **9,051 payments from 3,000 generated payers**, using **12 past-only features** (merchant/payer payment history and preceding refunds/disputes). Training uses a chronological **60/20/20 split**; selection compares rules, logistic regression, and XGBoost. The selected XGBoost model uses **Platt calibration** and **TreeSHAP** explanations.

| Metric | Held-out synthetic test |
| --- | ---: |
| PR-AUC | 0.348 |
| ROC-AUC | 0.841 |
| Precision at selected threshold | 28.2% |
| Recall at selected threshold | 61.5% |
| Brier score | 0.033 |

These are **offline synthetic test results**, not production fraud-prevention or recovered-revenue claims. The fixed validation threshold flagged 9.4% of a later test window despite an 8% validation review-capacity goal; monitoring and shadow policies exist partly to reveal such changes. Scores for Sandbox payments illustrate the pipeline, **not a calibrated real-world fraud probability**.

See [ML methodology](docs/ML_METHODOLOGY.md) for split integrity, leakage controls, model comparison, reproducibility, and evaluation limitations.

## Architecture

```mermaid
flowchart TD
  PP[PayPal Sandbox API & webhooks] --> ED[Supabase Edge webhook receiver]
  ED --> IN[(Private durable inbox)]
  IN --> BR[Supervised bridge / retries / deduplication]
  BR --> API[FastAPI application]
  API <--> DB[(PostgreSQL 16)]
  API --> ML[XGBoost + Platt + TreeSHAP]
  ML --> CASE[HIGH-risk review case]
  CASE --> AI[Gemini agent / read-only tools]
  CASE --> EV[Private evidence + PDF packets]
  AI --> HUMAN[Human review and approvals]
  EV --> HUMAN
  WEB[React + TypeScript web app] <--> API
  API --> LAB[Policy Lab / monitoring / relationship graph]
```

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, GSAP, React Query, AG Grid |
| API and auth | Python 3.12+, FastAPI, SQLAlchemy, Pydantic, session cookies, CSRF, merchant-scoped RBAC |
| Storage | PostgreSQL 16, Alembic migrations; private evidence/packet storage |
| Risk model | XGBoost, NumPy, scikit-learn and SHAP in offline training/evaluation |
| AI | Pydantic AI with Google Gemini in the verified hosted staging configuration |
| Payments and events | PayPal REST Sandbox, Supabase Edge Functions/inbox and durable processing workers |
| Hosting and QA | Render Docker staging, GitHub Actions, pytest, Vitest, Playwright |

**Data provenance is explicit:** `LIVE_SANDBOX`, `SYNTHETIC_DEMO`, `SIMULATED`, and merchant-provided records are labelled rather than blended into a claim of genuine customer activity.

## Hosted staging verification

As of **13 November 2026**, the deployed Render staging application has had the following verified or owner-confirmed checks:

- **Render application and PostgreSQL:** deployed with healthy readiness responses.
- **PayPal Sandbox:** hosted OAuth status displayed **OK**, with credentials and webhook ID configured.
- **Gemini 3.1 Flash Lite:** a real hosted investigation completed with model-generated, grounded findings, citations, and seven recorded investigation tool calls.
- **Supabase bridge:** hosted readiness checks passed; the owner also confirmed Sandbox webhook processing.
- **Judge demo:** isolated synthetic viewer was prepared and the enabled release deployed successfully.

These observations do **not** establish production eligibility, guaranteed availability, external provider certification, or real-money payment/refund functionality. The judge's **prebuilt deterministic** case is different from the **hosted Gemini** case demonstrated through an analyst session.

## Run locally

Prerequisites: **Python 3.12+**, **Node.js 24**, **PostgreSQL 16** (or Docker Desktop), and Git.

### 1. Database

From the repository root:

```bash
docker compose up -d --wait db
```

### 2. API

```bash
cd apps/api
python -m venv .venv
# Linux/macOS:
.venv/bin/python -m pip install -e ".[dev]"
cp ../../.env.example .env
```

On Windows PowerShell, use `py -3.12 -m venv .venv`, `.\.venv\Scripts\python.exe` instead of `.venv/bin/python`, and `Copy-Item ..\..\.env.example .env` instead of `cp`.

Before starting, edit **`apps/api/.env`**:

- Keep `SENTINEL_DATABASE_URL=postgresql+psycopg://sentinel:sentinel@127.0.0.1:5432/sentinel` for the example Docker database.
- Set `SENTINEL_PAYPAL_MODE=fixture` for a safe local demo **without PayPal credentials**.
- Set `SENTINEL_AI_PROVIDER=none` to use clearly labelled deterministic summaries.
- Supply a noncommitted `SENTINEL_SEED_ADMIN_PASSWORD`, at least one strong unique password. Optionally supply separate analyst/viewer seed passwords.

Then, from `apps/api`:

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed
.venv/bin/python -m app.cli demo-load --if-empty
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The synthetic scenario contains 9,051 payments; only its held-out portion is scored for the reproducible review demonstration. Seeded logins are `admin@northwind.example` and (if their passwords were set) `analyst@northwind.example` / `viewer@northwind.example`.

### 3. Web app

In another terminal:

```bash
cd apps/web
npm ci
npm run dev
```

Visit **http://localhost:5173**. The public homepage and simulated payment dossier do not require an account; the authenticated workspace uses the local seeded credentials. The one-click public judge-login flag is **off by default and restricted to the reviewed Render staging environment**.

For intentional Sandbox and Gemini setup, use the separate [PayPal integration guide](docs/PAYPAL_INTEGRATION.md), [agent design](docs/AGENT_DESIGN.md), [provider staging activation](deploy/render-provider-activation.md), and [safe judge access](deploy/public-judge-demo.md). **Do not commit API keys or enable financial execution.**

## Tests

CI covers backend tests, model reproducibility, OpenAPI contract consistency, frontend type checking/lint/unit tests, and container/browser-specific workflows.

```bash
# From apps/api
.venv/bin/python -m pytest

# From apps/web
npm run typecheck
npm run lint
npm test
npm run build
```

See [GitHub Actions](https://github.com/harshjha15335/SENTINEL-/actions) and [testing notes](docs/TESTING.md). Provider authentication and real webhook delivery are separate from offline unit tests.

## Safety and limitations

- **No PayPal production API mode.** Checkout is restricted to Sandbox or explicitly labelled fixture/simulated activity.
- **No real-money recovery.** Refund execution and external dispute submission are disabled in staging; approval does not imply execution.
- **Human-controlled decisions.** AI tools are read-only. Financial actions require separate authorization, and the demonstration viewer cannot perform them.
- **Synthetic model training.** Scores and model metrics must not be marketed as validated for real customer fraud.
- **Scoped access.** Sessions, CSRF, merchant isolation, rate limits, protected evidence, webhook verification/deduplication and auditable actions are part of the design.
- **Staging-only TLS exception.** The approved Render internal PostgreSQL connection uses encrypted `sslmode=require` without server-identity verification. It is not a production security profile.

## Project links and documentation

- **Website:** https://sentinel-v2-staging.onrender.com/
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **ML methodology:** [docs/ML_METHODOLOGY.md](docs/ML_METHODOLOGY.md)
- **Webhook operations:** [docs/WEBHOOK_OPERATIONS.md](docs/WEBHOOK_OPERATIONS.md)
- **Render integration runbook:** [deploy/render-provider-activation.md](deploy/render-provider-activation.md)
- **Public judge experience:** [deploy/public-judge-demo.md](deploy/public-judge-demo.md)
- **Security:** [docs/SECURITY.md](docs/SECURITY.md)

Historical development reports under `docs/` document earlier blockers and may predate the current hosted Sandbox/Gemini staging deployment.

## License

[Apache-2.0](LICENSE). SENTINEL is an independent hackathon project; it is not an official PayPal fraud product or a PayPal production integration.
