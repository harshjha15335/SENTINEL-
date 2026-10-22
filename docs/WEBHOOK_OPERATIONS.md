# Supabase → FastAPI webhook operations

The recovered application now forwards inbox deliveries to the existing FastAPI webhook route over HTTP. The receiver stays deployed at `https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook`; its downloaded ESZIP runtime was compared with transpiled local source using normalized syntax trees. Both runtime modules match. No receiver redeployment was needed for this integration.

## Acceptance and processing lifecycle

1. The Edge Function verifies the sandbox signature through PayPal and calls `sentinel_enqueue_webhook`. Raw UTF-8 body text and original transmission headers are retained. The public receiver cannot set a fixture origin.
2. Supabase atomically claims one due receipt with `FOR UPDATE SKIP LOCKED`, a random lease token and a two-minute expiry. Genuine and SIMULATED claims use distinct origin filters. Claim/renew/finish functions are service-role only.
3. Immediately before forwarding, the bridge renews and validates its lease. It POSTs the original bytes and original PayPal header values to `/api/v1/webhooks/paypal`.
4. FastAPI independently verifies the original signature against `SENTINEL_PAYPAL_WEBHOOK_ID`, commits the exact raw payload and event, and returns a durable receipt containing the provider event ID, SHA-256, verification status and data origin. A certificate-service outage returns 503 rather than treating a transient fetch failure as an invalid signature.
5. The bridge checks every receipt field and only then acknowledges Supabase. Attempted HTTP requests, unexpected 200 responses, timeouts or partial receipts never qualify as durable acceptance. A lost acknowledgement is safe to replay.
6. Existing local event reconciliation locks the event and transaction. Successful capture reconciliation sets the occurrence time and atomically creates a unique durable scoring job. Scoring uses the unchanged model and history rules; a HIGH result opens a review case through the existing case service.
7. The pipeline worker commits the assessment, automatic case and job completion in one transaction. Job claims expire after crashes and completion requires the current token. A transaction has one automatic webhook scoring job; an existing assessment is reused rather than automatically duplicating it.

Supabase `PROCESSED` means **durably accepted by FastAPI**, not proof that a payment was owned, scored or resolved. Local event/job states describe those later stages. Unknown transactions retain the existing IGNORED behavior; ingestion does not fabricate merchant transactions. Simulator-origin records never mutate genuine sandbox transactions.

## Retry and terminal states

- Inbox states: `PENDING`, `RUNNING`, `PROCESSED`, `DEAD`.
- A failed delivery uses exponential retry delay, capped at 300 seconds. A crashed claim becomes available after its lease expires. A stale/expired token cannot renew or finish another claim.
- Definitive invalid requests become `DEAD`; temporary connection/provider/API failures retry. After ten inbox claims an exhausted receipt becomes `DEAD`. Original payload and headers remain stored for investigation.
- Scoring jobs use the same four state names, a two-minute lease, exponential backoff capped at 300 seconds and a five-attempt limit. Assessment/case writes roll back on failure.
- Existing event retries are bounded to five attempts and now have `next_attempt_at` backoff. A `FAILED` event at that limit is reported as exhausted in operations metrics.
- Never edit signed bodies to repair a delivery. Investigate configuration/ownership first, then an administrator may reset an explicitly selected failed receipt's state/attempts/availability. Do not reset unrelated or genuine rows while running fixture tests.

These are at-least-once transports with idempotent database effects, not an exactly-once HTTP delivery claim. In-flight requests can overlap after a crash or timeout; event uniqueness, payload-conflict rejection, row locks and atomic scoring completion prevent duplicate effects.

## Required configuration (names only)

| Process | Runtime settings |
|---|---|
| Python API and pipeline | `SENTINEL_DATABASE_URL`, `SENTINEL_PAYPAL_WEBHOOK_ID` |
| Supabase bridge | `SENTINEL_SUPABASE_URL`, `SENTINEL_SUPABASE_SERVICE_ROLE_KEY` |
| Bridge HTTP destination | Optional `SENTINEL_BRIDGE_API_URL`; defaults to loopback HTTP using `PORT` (or 8040) |
| Hosted security | `SENTINEL_ENVIRONMENT`, `SENTINEL_COOKIE_SECURE`, `SENTINEL_STORAGE_BACKEND`, `SENTINEL_REQUIRE_WORKERS_READY` |
| Listener/proxy | `HOST`, `PORT`, optional trusted `SENTINEL_FORWARDED_ALLOW_IPS` |
| Sandbox checkout, if enabled | `SENTINEL_PAYPAL_MODE`, `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET` |

Use production environment, secure cookies behind HTTPS, database evidence storage and workers-required readiness for a hosted integration. The service-role key is server-only: no `VITE_` variable, browser storage, source-code literal or build argument may contain it. Supabase Management API access is needed for migration/deployment administration, not for normal bridge operation. The bridge can operate without a Supabase personal access token.

The current cloud runtime uses a mode-600 private environment file outside Git. The service-role key was obtained through existing authenticated project access and was never printed. The Webhook ID was provided separately by the user. PayPal secrets inside an Edge Function are not automatically injected into the Python process.

## Startup and supervision

From `apps/api`, apply `alembic upgrade head`, then run `python -m app.workers.supervisor`. The supervisor starts:

- Uvicorn serving the existing API/frontend;
- `app.workers.pipeline`, which recovers event processing and scoring jobs;
- `app.workers.supabase_inbox`, when a Supabase URL is configured.

Children restart after failure with a bounded restart budget; exhausted budgets stop the supervisor so the hosting platform can report/restart the unhealthy container. SIGTERM stops its managed children. The pipeline holds a PostgreSQL advisory lock for its lifetime; a duplicate pipeline process exits instead of racing the first one. Inbox claims remain independently safe across multiple bridge instances.

In this prepared environment, the retained startup helper is `/workspace/sentinel-environment/start-integration.sh`. It starts the existing PostgreSQL service, applies migrations and launches the supervisor. Private files are sourced without printing values. Current local HTTP is restricted to loopback; it is not a public hosted HTTPS API. Cookies are configured for local HTTP only here, while the proposed hosted configuration enables secure cookies.

## Health, metrics and access

- `/api/v1/ready` verifies database/migration state. With `SENTINEL_REQUIRE_WORKERS_READY`, both pipeline and genuine bridge heartbeats must be HEALTHY and less than 45 seconds old.
- `/api/v1/operations/webhooks` is administrator-only. Event/job counts are scoped to the signed-in merchant, and worker health includes heartbeat, completed-task count, failure count and error category. It reports exhausted local events separately. Worker task counts are not a count of unique payments.
- Supabase RPC `sentinel_webhook_metrics` reports inbox counts and age by origin/state for server-role operators; it is unavailable to browser roles.
- Operational logs contain categories and acceptance outcomes, not credential values, raw bodies or upstream error responses.

Verified against the running local application: administrator login, `/api/v1/me` session access, CSRF rejection, viewer denial of operations metrics, anonymous denial, and production fixture-route rejection. Controlled API termination preserved the existing login session after supervisor restart. A killed pipeline worker restarted, and an extra pipeline worker was rejected by its advisory lock.

## Deterministic tests and fixture separation

Normal production forwarding accepts only `LIVE_SANDBOX` inbox claims. The hidden `/api/v1/webhooks/fixtures/paypal` endpoint requires both an explicit non-production setting and a server-side HMAC key. Production configuration refuses enabling fixtures. Fixture IDs must start `FIXTURE-`, the private enqueue RPC fixes origin to `SIMULATED`, and only SIMULATED transactions may be reconciled through that route.

The local fixture receiver in `scripts/fixture-webhook-receiver.ts` injects mock PayPal verification and writes to the private fixture RPC. It is never deployed and never calls PayPal. The hosted production receiver and genuine receipts are not used as test fixtures.

Authorized end-to-end check:

```bash
# Source private server configuration without displaying it first.
apps/api/.venv/bin/python scripts/verify-webhook-pipeline.py --allow-hosted-fixtures
```

The check uses the actual hosted Supabase private inbox, an isolated `sentinel_integration` database, loopback FastAPI, the HTTP bridge and the existing model. It verifies duplicate receipt handling, abandoned-lease reclamation, an actual API outage/restart, stale acknowledgement rejection, out-of-order capture status and terminal rejection of an invalid fixture HMAC. The fixed history produces HIGH naturally with the existing model; its result remains a functional fixture result, not a fraud benchmark or provider verification. Fixture child processes are stopped afterward.

Backend tests additionally cover concurrent scoring workers, scoring-lease recovery, bounded failed-job retries, no partial assessment/case on failure and generic HTTP 200 responses without durable proof. Supabase SQL tests cover RLS/grants, disjoint claims and retained exhausted receipts.

No real PayPal sandbox payment was initiated. The user's instruction to skip that test remains in effect.

## Evidence, backups and hosted runtime

Evidence remains in the application's private `stored_blobs` table when database storage is configured. It is not exposed as a static directory. A local PostgreSQL custom-format dump was restored into a separate database; business-row counts and all four stored evidence/packet blobs matched byte-for-byte. The dump is mode 600 outside Git. This verifies local backup restoration, not a hosting provider's backup schedule, retention or point-in-time recovery.

The container now launches the supervisor under its non-root user. Source and entrypoint permissions support non-root execution; optional build CA trust uses an ephemeral BuildKit secret, preserving TLS verification. Runtime secrets, evidence directories and database dumps are excluded from the build context.

`deploy/render-continuous.yaml` is a concrete, review-only proposal for a continuously running container and managed PostgreSQL. Its starter/database plans are billable. It has not been applied, no services were purchased, no credentials were published and auto-deploy is disabled. The older free-demo blueprint is not a continuous-hosting readiness claim.

Public application HTTPS, persistent hosted application database/evidence, platform restart policy and provider backups still require a hosting account and explicit cost authorization (or an existing suitable host). Only the Supabase receiver is currently public. Do not describe the full Python application as hosted until that deployment is actually completed and tested.

## Current network limitation

Read-only certificate-host reachability checks returned proxy HTTP 403 for `api.sandbox.paypal.com`, `api.paypal.com` and `api-m.paypal.com`. These hosts are allowed by the signature verifier but require activation of the saved cloud network draft before genuine events can be verified reliably. Saving a draft does not activate it. No real payment was initiated.

## Session 8 operations interface

The administrator-only `/operations` page consumes the typed `/api/v1/operations/webhooks` endpoint. Merchant event/job/investigation counts are grouped by origin. Worker health includes freshness, last successful work, failures and error category. Idle polling never advances last-success time. Evidence file counts/byte totals are merchant-scoped database observations, not backup attestations.

The bridge samples `sentinel_webhook_metrics` every 30 seconds into private worker metadata. Metrics failure does not prevent delivery; snapshots older than 90 seconds are shown stale. Requests never expose global inbox payloads. Set `SENTINEL_OPERATIONS_INBOX_MERCHANT_ID` to the installation operator merchant UUID if its administrators should see global origin/state aggregates; it is hidden from all other tenants and disabled by default. This setting is an installation privilege, not a general merchant permission.

Application migration `8ab7245e13c0` adds nullable worker last-success and inbox snapshot fields. Exact-head readiness now rejects an incompatible schema. Container health uses readiness. Startup upgrades only the reviewed migration target; `SENTINEL_AUTO_MIGRATE=false` disables automatic upgrading and `python -m app.cli check-schema` rejects mismatched schemas before supervision starts.

`SENTINEL_HOSTED_DEPLOYMENT=true` enforces production, secure cookies, database evidence, required worker freshness and HTTPS-only/empty CORS. Hosted supervision rejects wildcard proxy trust. These checks do not provision a host or verify its TLS termination and backups.

The old certificate-host limitation above is historical: current requests pass proxy CONNECT and TLS verification. Runtime sandbox OAuth still fails AUTHENTICATION. See PROVIDER_VERIFICATION.md. Startup instructions were saved without publishing configuration; no new cloud network permissions were added in Session 8.
