# Environment setup and integration diagnostics

Use the recovered checkout and its preserved lineage. Never reset it to public main. Install the pinned existing API dependencies and web lockfile, build the frontend, and provision a separate PostgreSQL application database.

## Server-side variable names

- Application: `SENTINEL_DATABASE_URL`, `SENTINEL_ENVIRONMENT`, `SENTINEL_WEB_DIST`, `HOST`, `PORT`.
- Hosted security: `SENTINEL_HOSTED_DEPLOYMENT`, `SENTINEL_COOKIE_SECURE`, `SENTINEL_CORS_ORIGINS`, `SENTINEL_STORAGE_BACKEND`, `SENTINEL_REQUIRE_WORKERS_READY`, `SENTINEL_FORWARDED_ALLOW_IPS`.
- Bridge: `SENTINEL_SUPABASE_URL`, `SENTINEL_SUPABASE_SERVICE_ROLE_KEY`, optional `SENTINEL_BRIDGE_API_URL`. Service-role credentials are never browser/VITE variables.
- PayPal sandbox: `SENTINEL_PAYPAL_MODE`, `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET`, `SENTINEL_PAYPAL_WEBHOOK_ID`.
- AI: `SENTINEL_AI_PROVIDER`, `SENTINEL_AI_MODEL`, `SENTINEL_AI_API_KEY`. Existing `SENTINEL_INVESTIGATION_*` names do not configure the provider adapter.
- Safe gates: `SENTINEL_REFUND_EXECUTION_ENABLED=false` by default. Production environment refuses execution even if this flag is set. Dispute external submission has no enabling flag.
- Migrations/demo: `SENTINEL_AUTO_MIGRATE`, `SENTINEL_MIGRATION_TARGET=d105a4143283`, `SENTINEL_JUDGE_PASSWORD`, optional `SENTINEL_OPERATIONS_INBOX_MERCHANT_ID`.
- Administration only: `SUPABASE_ACCESS_TOKEN`; not required for normal bridge polling.

Enter secrets through secure server/runtime settings, not source code, browser configuration or chat. PayPal Basic OAuth encodes the credential pair: a proxy placeholder is not established as a transferable raw runtime secret. Keep the official SDK/client construction; correct the supported credential delivery binding or securely supply the actual paired runtime credential instead of attempting to extract proxy-held secrets. Restart the process after environment rotation, or use the trusted in-process `rotate_credentials` method, which invalidates cached tokens. There is no public credential-rotation route.

## Current exact external blockers

Approved metadata shows `*.supabase.co`, but a request to `cfslzvvdjxstpupkqbpw.supabase.co` is denied at CONNECT before Supabase receives it. This is not a remote API-key 403. The managed environment's active policy lacks the three certificate-host additions present in the saved draft. The exact project hostname was added to that draft for explicit scope. Review/save and publish through environment settings, then retest; draft save alone does not activate policy or establish a new snapshot. If the exact project host remains denied, ask the environment administrator to inspect the proxy enforcement/scope, naming that host and bridge POSTs to `/rest/v1/rpc/`.

Required HTTPS destinations: the exact Supabase project, `api-m.sandbox.paypal.com` for sandbox OAuth/REST, and verifier-approved certificate hosts `api.sandbox.paypal.com`, `api.paypal.com`, `api-m.paypal.com`. `api.supabase.com` is administrative. Do not broaden to all Internet hosts or bypass the proxy. Keep certificate/TLS verification enabled.

The current nonfinancial OAuth probe reaches PayPal and returns HTTP401 `invalid_client`. This proves the submitted pair/binding is not accepted, not which credential is wrong. The official authentication document was fetched from `https://developer.paypal.com/api/rest/authentication/`; request construction remains client-credentials + Basic authentication. Never log error-description text or tokens. No genuine financial request is required to diagnose authentication.

## Safe verification

Check `/api/v1/health` for process liveness and `/api/v1/ready` for schema/essential-worker readiness. Inspect administrator `/operations` and its snapshot age. A running bridge PID is insufficient; a successful poll and fresh heartbeat are required. Do not turn off required readiness to hide this failure. Optional AI configuration is not a database dependency and does not block local deterministic investigations.

No real provider authentication, event delivery, inference or financial result is established by mocks. Genuine payment/refund/dispute tests and potentially billable AI/hosting operations require separate authorization.

## Fixture and tracing semantics

Fixture-mode `/paypal/status` returns `token_check=not_attempted` and makes no credential probe. Only the real sandbox path can report successful OAuth. The bridge hashes the stable provider event ID into a bounded `X-Correlation-ID` and logs `event_trace_id`; API middleware preserves it across duplicate HTTP deliveries. Durable provider-event IDs and linked transaction/case/job/investigation/packet IDs support later database tracing. No signature header or signed body is rewritten.

Worker metadata separately records `last_successful_poll_at` and accepted-task time. An idle successful poll can update the former without inventing a processed event. Failed polls retain the last known successful-poll timestamp; inbox snapshot observation time advances only when real metrics are fetched.
