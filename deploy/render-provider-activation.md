# Guarded provider activation on the existing Render staging service

This runbook applies only to Render service `srv-dbqq91tbedkc73eds3v0`, staging project `prj-dbq48lon74is739m7nl0`, workspace `tea-d8gorhflk1mc73f4pmr0`, and the existing `sentinel_staging` internal PostgreSQL database. Do not copy the flags to production or another staging stack.

## Safety model

The default deployment continues using `SENTINEL_PAYPAL_MODE=fixture` and `SENTINEL_AI_PROVIDER=none`, even if previously saved credentials exist. No active providers start unless the corresponding explicit opt-in flag is true.

For Google Gemini staging, set the following **together**, after verifying the key is saved in Render (never in Git):

```dotenv
SENTINEL_STAGING_AI_ENABLED=true
SENTINEL_AI_PROVIDER=google
SENTINEL_AI_MODEL=gemini-3.1-flash-lite
SENTINEL_AI_SDK_MAX_RETRIES=0
SENTINEL_AI_REQUEST_LIMIT=4
SENTINEL_AI_MAX_OUTPUT_TOKENS=1024
# SENTINEL_AI_API_KEY=<secret in Render Environment>
```

For PayPal Sandbox staging, set the following **together**, after verifying the PayPal paired Sandbox keys and Supabase service-role key are saved securely in Render:

```dotenv
SENTINEL_STAGING_PAYPAL_SANDBOX_ENABLED=true
SENTINEL_PAYPAL_MODE=sandbox
# SENTINEL_PAYPAL_CLIENT_ID=<secret in Render Environment>
# SENTINEL_PAYPAL_CLIENT_SECRET=<secret in Render Environment>
# SENTINEL_PAYPAL_WEBHOOK_ID=<signed Sandbox webhook ID in Render Environment>
# SENTINEL_PAYPAL_RETURN_URL=<reviewed public HTTPS return URL>
# SENTINEL_PAYPAL_CANCEL_URL=<reviewed public HTTPS cancel URL>
# SENTINEL_SUPABASE_URL=https://cfslzvvdjxstpupkqbpw.supabase.co
# SENTINEL_SUPABASE_SERVICE_ROLE_KEY=<secret in Render Environment>
```

Never enable refund execution or fixture webhook ingress. Retain the existing source-controlled guards: hosted deployment, HTTPS cookies, database evidence storage, pinned database name/host/user/project/workspace, hard SSL requirement, narrow forwarded proxy ranges and worker readiness. If a bridge is enabled, readiness must include a fresh successful Supabase worker heartbeat, not merely a running process.

**TLS caveat:** The approved Render private PostgreSQL staging exception uses `sslmode=require`. Connections are encrypted, but server identity is **not** verified. This is not appropriate for production or genuinely sensitive customer transactions. Enabling provider integration under this exception should be understood as an explicitly limited Sandbox-only staging risk, never an upgrade to authenticated database TLS.

## Safe rollout

1. Keep Render auto-deploy disabled. Merge only after CI and focused negative tests pass, then manually deploy the code while both provider flags remain off. Verify `/api/v1/ready` and current UI before changing mode.
2. Inspect Render's Environment screen privately. If *any* expected key or webhook ID is missing, stop that provider's activation; do not substitute placeholders, pass secrets in URLs, retrieve secret values into agent output or enable an incomplete mode.
3. Enable Gemini separately by setting its explicit flag and provider options, deploy, verify readiness, provider status and one user-authorized synthetic-only investigation through authenticated UI. Enforce request/token limits and monitor quota. The local one-request and 4-turn verifiers do not prove Render's key is valid.
4. Enable PayPal Sandbox separately *only* after webhook callback URL/ID, verified paired credentials and Supabase bridge configuration are present; deploy and verify read-only sandbox OAuth and bridge health. Never initiate a real payment, capture, refund or dispute submission as part of a connectivity check.
5. Confirm workers, TLS, auth, CSRF, CORS and tenant isolation and retain a viable rollback. Stop if the backend returns 503, restarts repeatedly, lacks verified provider connectivity or starts receiving unintended live events.

## Recovery

To revert Gemini safely, set `SENTINEL_STAGING_AI_ENABLED=false` and `SENTINEL_AI_PROVIDER=none`. To revert PayPal safely, set `SENTINEL_STAGING_PAYPAL_SANDBOX_ENABLED=false` and `SENTINEL_PAYPAL_MODE=fixture`; bridge will be dormant in hosted fixture stage. Keep credentials stored securely without exposing them. Redeploy the previous verified code ref if a configuration-only rollback is insufficient. Do not delete or reset PostgreSQL or Supabase data.
