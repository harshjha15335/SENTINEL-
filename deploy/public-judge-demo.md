# Public homepage + safe read-only judge demo (Render staging)

The normal Render build now serves the existing cinematic Follow the Money story at `/`. The already public `/demo-payment` remains a fully synthetic, non-API preview. `/login` remains the merchant sign-in page and `/intro` remains authenticated.

**Judge entry:** a visible "One-click judge demo" control on `/` and `/login` sends an explicit same-origin POST to `/api/v1/auth/demo`. Only the approved Render staging instance can enable it; the default is DISABLED.

## Operator activation — exact staging only

Environment flag (never in public source or on production):

```dotenv
SENTINEL_PUBLIC_DEMO_LOGIN_ENABLED=true
```

Staging host and workspace are pinned in Settings. The current deployment requires all existing hosted protections (production security profile, staging stage, reviewed Render IDs/internal DB TLS scope, HTTPS cookies, database evidence storage, worker readiness, disabled financial execution and disabled webhook fixtures).

The next *manual* Render redeployment runs `python -m app.cli public-demo-init` in the pre-deploy command after schema checks. On an empty demo tenant it invokes the trusted `judge.prepare` routine and creates the isolated `SENTINEL isolated judge demo` tenant, `judge@sentinel-demo.example` VIEWER user, synthetic historical data, deterministic investigation, synthetic evidence, packet and pending internal approval. The viewer's unguessable password is not displayed or shared. If a previously provisioned demo tenant exists, it is reused without changing its password. If its data is missing or unsafe, the pre-deploy command fails and does not enable guest login.

The public endpoint never provisions users/merchants, writes transactions, generates AI output or calls PayPal. It checks the prepared tenant, refuses provider-origin records, rate-limits entries, requires an exact same-origin browser POST, rejects an existing signed-in session, then issues a 45-minute max VIEWER session with secure HttpOnly cookie, per-session CSRF secret and no-store response. Merchant API authorization and tenant scoping are unchanged. VIEWER cannot run new AI investigations, create PayPal orders, refund, approve or mutate review cases.

## Verification on deployed staging

1. `/` must present the story and two distinct paths: public `/demo-payment` and one-click read-only judge entry. Test desktop and mobile, no overflow, no broken links.
2. Fresh incognito browser: click judge entry. It should reach `/app/demo`, then allow read-only navigation to the prepared investigation, evidence and policy. Verify role VIEWER and merchant environment DEMO on Settings; test that write actions are not offered and API denies direct writes.
3. Separate signed-in admin session: guest button should *not* replace the admin session.
4. Invalid cross-origin POST should be forbidden. No-flag should return 404. Confirm no live merchant data, secret, credentials, real provider actions or true PayPal claims appear in public pages.
5. Do not interpret the prepared deterministic demo investigation as proof of live Gemini. The authenticated merchant workspace separately supports genuine hosted AI, already verified by the owner.

## Rollback

Set `SENTINEL_PUBLIC_DEMO_LOGIN_ENABLED=false` in Render and redeploy; the public endpoint becomes unavailable. Previously issued demo sessions remain valid until expiry or logout: this flag controls **new guest entry only**, not session revocation. Revert the code if further disabling is needed. Existing merchant accounts, DB, financial data and PayPal/Supabase settings are not deleted or modified.

The public landing page still works when the judge-login flag is disabled. No new Render resources are required.
