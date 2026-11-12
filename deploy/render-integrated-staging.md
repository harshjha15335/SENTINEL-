# SENTINEL — guarded PayPal sandbox and Gemini activation on Render

> **NOT ACTIVE / NOT APPROVED**. This is a prepared, opt-in security profile.
> Do not merge or enable it until the owner explicitly acknowledges the
> **encrypted-only internal database TLS** limitation and authorizes sandbox
> authentication, webhook forwarding, and potentially billable AI inference.

## Why a second policy is required

The existing `render_internal_staging` setting was approved for a synthetic-only
fixture installation. Saving secrets in Render does not extend its authorization.
Render's internal PostgreSQL TLS uses self-signed certificates: `sslmode=require`
requires encryption **but does not authenticate the server certificate/hostname**.
Render states that internal connections cannot use `verify-full`. Exact
account/project/host/database pinning and the private Render network reduce
but **do not remove** the risk of a wrong/internal malicious endpoint.

Default hosted production remains `verify-full`, and synthetic staging
remains `render_internal_staging` with inactive provider modes.

## Separate owner approval

Before turning this on, the owner must explicitly approve:

- Using the **existing** privately routed Render database with encrypted-only
  `sslmode=require` (no certificate/hostname verification) for sandbox events
  and investigation records in Staging. This differs from the earlier
  synthetic-only approval.
- Sending sandbox OAuth and webhook requests to PayPal, protected service-role
  RPCs to the existing Supabase project, and allowing optional AI inference
  charges from Gemini. Sandbox must never be confused with real money.
- Keeping `SENTINEL_REFUND_EXECUTION_ENABLED=false`, webhook fixtures off,
  one existing Render service/database and auto-deploy off.

No credit/card spending cap is established by the configured AI token budgets.

## Required staged prerequisites (secrets are never committed)

Credential values must be saved as Render service environment variables
and verified by real, nonfinancial credential probes before any user-facing
claim of connection:

- `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET`,
  `SENTINEL_PAYPAL_WEBHOOK_ID` (same PayPal Sandbox REST app)
- `SENTINEL_PAYPAL_RETURN_URL=https://sentinel-v2-staging.onrender.com/api/v1/paypal/return`
- `SENTINEL_PAYPAL_CANCEL_URL=https://sentinel-v2-staging.onrender.com/api/v1/paypal/cancel`
- `SENTINEL_AI_API_KEY`, `SENTINEL_AI_MODEL=gemini-3.1-flash-lite`
  (also supports stable `gemini-3.5-flash-lite` with verified account access)
- `SENTINEL_SUPABASE_URL=https://cfslzvvdjxstpupkqbpw.supabase.co`
- `SENTINEL_SUPABASE_SERVICE_ROLE_KEY` (server only)
- `SENTINEL_RENDER_INTERNAL_TLS_REVIEWED_HOST` must be the previously
  authenticated host from the exact linked Render database.

## Activation after explicit owner approval + passing tests

Change all four **nonsensitive** settings together in the existing Render service
(no new resources):

```
SENTINEL_DATABASE_TLS_POLICY=render_internal_integrated_staging
SENTINEL_RENDER_INTEGRATION_TLS_APPROVED=true
SENTINEL_PAYPAL_MODE=sandbox
SENTINEL_AI_PROVIDER=google
```

Retain the existing trusted proxies, exact Render workspace/project IDs,
`SENTINEL_REFUND_EXECUTION_ENABLED=false`,
`SENTINEL_ALLOW_WEBHOOK_FIXTURES=false`, secure cookies and required workers.
Do not put secrets in a GitHub commit or a frontend `VITE_` variable.

**Important:** changing Render environment variables via the connected Render
integration may immediately trigger a new deploy, even if Git auto-deploy is off.
The change must be atomic and performed only after all gates.

## Verification before saying 'connected'

1. Release: exact commit CI + Docker acceptance, no unapproved TLS fallbacks,
   migration/schema checks pass.
2. Startup: new Render deploy is live and `/api/v1/ready` returns 200; genuine
   Supabase bridge heartbeat and configuration are required for sandbox mode.
3. PayPal: authenticated sandbox OAuth returns a token (never display it);
   correct sandbox app/webhook ID, public callback and signature verification.
4. Gemini: model metadata/key authorization and a bounded investigation
   inference (if owner has approved use/charges); ensure deterministic fallback
   is clearly labeled, never claim it was a real model call.
5. Delivery: verified genuine PayPal *sandbox* event in Supabase inbox, bridge
   accepts/forwards event, transaction receives past-only risk score, HIGH
   risk case created and reflected in UI. An idle bridge or seeded fixture does
   not prove provider delivery.
6. Provenance: preserve `LIVE_SANDBOX` vs `SYNTHETIC_DEMO` throughout UI,
   reports, metrics and audit trails.

## Rollback

If startup/readiness, OAuth, bridge or Gemini verification fails, stop without
processing additional sandbox transactions. Restore the original four
nonsensitive settings in **one update**:

```
SENTINEL_DATABASE_TLS_POLICY=render_internal_staging
SENTINEL_RENDER_INTEGRATION_TLS_APPROVED=false
SENTINEL_PAYPAL_MODE=fixture
SENTINEL_AI_PROVIDER=none
```

Use the prior healthy Render deploy, retain database contents and secret values,
and do not roll back migrations or create another database. The upstream
pre-deploy and worker health gates remain mandatory.

Sources:
- https://render.com/docs/postgresql-creating-connecting
- https://www.postgresql.org/docs/current/libpq-ssl.html
