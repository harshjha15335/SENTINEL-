# Architecture

```mermaid
flowchart LR
  subgraph Browser
    SPA[React SPA<br/>Vite · Tailwind · Radix · AG Grid]
    PPJS[PayPal v6 JS SDK<br/>buyer approval]
  end
  subgraph API[FastAPI · apps/api]
    AUTH[Sessions · CSRF · RBAC]
    CHK[Checkout service]
    WH[Webhook intake<br/>signature verify]
    GW{{PayPalGateway protocol}}
    SBX[SandboxPayPalGateway<br/>HTTPX → api-m.sandbox.paypal.com]
    FIX[FixturePayPalGateway<br/>SIMULATED]
  end
  WORKER[Event worker<br/>python -m app.workers.events]
  DB[(PostgreSQL 16)]
  PP[(PayPal sandbox)]

  SPA -- /api/v1 same-origin cookies --> AUTH --> CHK --> GW
  GW --> SBX --> PP
  GW -.offline only.-> FIX
  PPJS -- approve order id --> PP
  PP -- signed webhooks --> WH --> DB
  WORKER --> DB
  CHK --> DB
```

## Request path for a sandbox payment
1. SPA calls `POST /api/v1/paypal/orders` with `{product_id, quantity}` and an `Idempotency-Key`. No amount is accepted (extra fields → 422).
2. API loads the product for the caller's merchant, computes the amount in minor units, inserts a `transactions` row (`ORDER_CREATED`, `data_origin` from the gateway) and calls `POST /v2/checkout/orders` with `PayPal-Request-Id`.
3. SPA hands the order id to the v6 `PayPalOneTimePaymentButton`; the buyer approves in PayPal.
4. `onApprove` calls `POST /api/v1/paypal/orders/{id}/capture`. The API locks the row (`SELECT … FOR UPDATE OF transactions`), returns early if already captured, otherwise captures with deterministic `PayPal-Request-Id = sentinel-capture-{txn}`, and compares the captured amount to the expected amount. Mismatch → `CAPTURE_FAILED` with reason, never `CAPTURED`.
5. PayPal sends `PAYMENT.CAPTURE.*` webhooks; intake verifies, stores, acknowledges, then reconciles (status precedence prevents regression).

## Module boundaries (`apps/api/app`)
- `core/` config (typed env), JSON logging with redaction, correlation-id + security-header middleware, domain errors → consistent error objects.
- `auth/` passwords, sessions, rate limit, role dependencies.
- `models/` SQLAlchemy models and enums (single source of domain states; exported to the SPA via OpenAPI).
- `services/paypal/` gateway protocol, sandbox REST, fixture, parsing, factory.
- `services/` checkout, transactions, webhooks, audit.
- `api/v1/` thin routers.
- `workers/` durable event re-driver.

## Operating modes
- `SENTINEL_PAYPAL_MODE=sandbox` (default): real sandbox requests; requires credentials, otherwise order endpoints return 503 with `credential_dependency: true` (no silent fallback).
- `SENTINEL_PAYPAL_MODE=fixture`: offline; every record is `SIMULATED` and the UI shows "Simulated gateway".
- No live mode exists.

## Delivery plan (parallel, deadline 2026-11-12)
| Week of | Payments/backend | ML | AI/evidence | Frontend |
|---|---|---|---|---|
| Oct 10 | Phase 0–1 slice ✅, Phase 2 webhooks ✅ | Dataset download scripts, Track B generator | — | Shell, tokens, 5 screens ✅ |
| Oct 17 | Live sandbox run, cases + review queue | Track A/B training, evaluation report | Agent tools + schema | Workbench layout |
| Oct 24 | Approvals + refund path, disputes capability detection | SHAP in API | Evidence upload + packet PDF | Workbench, evidence drawer |
| Oct 31 | Graph analytics, policy lab | Policy cost model | Prompt-injection tests | Graph explorer, policy lab |
| Nov 7 | Deploy (Render + Vercel), security pass | — | — | Polish, video recording |
