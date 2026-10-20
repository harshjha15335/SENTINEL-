# Supabase-hosted PayPal webhook

SENTINEL can receive PayPal sandbox callbacks through a Supabase Edge Function without exposing the local FastAPI server through a tunnel. This hosts the webhook receiver and a private durable inbox; the existing Python application and its PostgreSQL database remain separate.

Implementation is on `feature/supabase-webhook`, based on the recovered Phase 4 commit `6cdd3d12f63ff42f1dee13db1145b7b69209bb5d`. The recovery branch, backup refs, original checkout and recovery bundle remain preserved.

## Current deployment state

No Supabase project or public URL has been created. There is no Supabase account login/access token in this environment. Local passing tests do not establish a hosted deployment or a real PayPal delivery.

The deployment script is ready to create a project in an accessible organization, install the private inbox, deploy the function and check its public URL. It requires an account-owned `SUPABASE_ACCESS_TOKEN`. Create/sign in to your account at https://supabase.com/dashboard, then create a personal access token at https://supabase.com/dashboard/account/tokens and enter it in secure environment settings. Do not paste it into chat or a shell command.

Network requirements `api.supabase.com` and `*.supabase.co`, plus the access-token requirement, were saved in the environment draft. Review/save and publish those environment changes before using them. Draft persistence does not provide account credentials or prove network connectivity.

## Create and deploy

The tested tooling in this environment is Deno 2.9.6 and the official checksum-verified Supabase CLI 2.54.11. Outside this environment, install the official CLI using Supabase's instructions. Here, run:

```bash
cd /workspace/SENTINEL-recovered
SUPABASE_CLI=/workspace/sentinel-tools/bin/supabase python scripts/deploy-supabase-webhook.py
```

The script uses `SUPABASE_ACCESS_TOKEN` from the environment. With exactly one organization it selects that organization; otherwise set non-secret `SUPABASE_ORGANIZATION_ID` to your chosen organization. It creates a project named `sentinel-<random suffix>` in `ap-south-1` by default. `--region` selects another region. Supabase billing follows the selected organization's plan; the script does not upgrade plans or request a larger instance.

Private resumable state, including the generated database password, is saved outside Git in a mode-700 directory with a mode-600 state file. Default: `/workspace/sentinel-supabase-private/deployment.json`. `SENTINEL_SUPABASE_STATE_DIR` can select another private directory. If creation times out ambiguously, rerunning checks the account's projects rather than blindly creating a duplicate. If the result remains unknown, inspect the dashboard and resume with `--project-ref <ref>`.

The script applies `supabase/migrations/202610200001_webhook_inbox.sql` through the Management API and deploys `paypal-webhook` with `--use-api`. Docker is not required for that deployment. The function's Supabase JWT check is disabled because PayPal sends its own signature; handler signature verification is mandatory. The script verifies HTTP 200 on GET and rejection of an unsigned POST with HTTP 400 before printing a public URL.

The final URL will have this form, using the actual reference returned by Supabase:

```text
https://<project-ref>.supabase.co/functions/v1/paypal-webhook
```

This differs from the FastAPI route `/api/v1/webhooks/paypal`. Register the function URL itself when using Supabase.

## Configure PayPal

1. Deploy first to obtain the real URL.
2. Register that exact URL in the PayPal **sandbox** REST app's webhooks settings.
3. In Supabase Dashboard → Edge Functions → Secrets, set:
   - `SENTINEL_PAYPAL_CLIENT_ID`
   - `SENTINEL_PAYPAL_CLIENT_SECRET`
   - `SENTINEL_PAYPAL_WEBHOOK_ID` (the ID returned for this registered function URL).
4. Configure the same webhook ID in the SENTINEL inbox bridge. A webhook ID belonging to a different registered URL will not verify correctly.

The deployed function receives `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from Supabase's built-in server environment. Do not put the service-role key in browser configuration. The deployment script deliberately does not copy PayPal secrets from proxy-backed cloud variables into Supabase: those bindings may contain placeholders instead of transferable raw secrets. Enter provider values directly in Supabase's secure settings.

A GET is a liveness check. Receiving real signed events additionally requires all PayPal secrets above. Missing secrets return a retryable 503 for otherwise plausible signed POSTs. No simulator fallback or production-money PayPal mode is enabled; OAuth and verification requests go only to `api-m.sandbox.paypal.com`.

## Connect to the existing payment processor

On the machine running SENTINEL, securely configure:

- `SENTINEL_SUPABASE_URL=https://<project-ref>.supabase.co`
- `SENTINEL_SUPABASE_SERVICE_ROLE_KEY` from that project's server-only API settings.
- `SENTINEL_PAYPAL_WEBHOOK_ID` matching the registered function URL.
- The existing `SENTINEL_DATABASE_URL` for the SENTINEL application database.

Then run the bridge as a supervised long-running process:

```bash
cd /workspace/SENTINEL-recovered/apps/api
.venv/bin/python -m app.workers.supabase_inbox
# One poll for diagnostics:
.venv/bin/python -m app.workers.supabase_inbox --once
```

The worker claims a bounded batch, independently verifies the signature over the original raw body using the existing PayPal certificate verifier, commits the event locally, runs the existing transaction reconciler, then acknowledges the Supabase receipt. It does not trust a database row's claim to be verified. If the local application is offline, the receipt remains in Supabase until a bridge runs. This function alone does not host the Python API, risk engine or investigation workbench.

Existing transaction matching and event status precedence remain in effect. Unknown transactions are recorded as ignored by the existing processor; a Supabase receipt is not proof a payment was updated. The bridge does not create merchant payments from unowned events or perform refunds.

## Persistence, permissions and retry behavior

- RLS is enabled on `public.sentinel_webhook_inbox`. Anonymous and authenticated browser roles have no table or RPC privileges. Only the server service role may enqueue, claim or acknowledge.
- A unique provider-event ID deduplicates concurrent deliveries. A repeated ID with different raw bytes returns a conflict rather than replacing the original evidence.
- The function returns success only after the database commit. Verification/provider/database failures are not acknowledged as successful receipts.
- Worker claims use `FOR UPDATE SKIP LOCKED`, random lease tokens and a two-minute lease. A stale worker cannot acknowledge a replacement worker's lease.
- A lost acknowledgement retries safely through SENTINEL's existing unique event IDs and processor locks. A failed delivery becomes available after one minute; a crashed lease becomes available after two minutes.
- After ten claims a still-unprocessed row stays stored for operator review and is excluded from automatic claiming. Inspect `attempts`, `processed_at`, `available_at` and `last_error` through a privileged server/dashboard session. After fixing the cause, an administrator can reset `attempts=0` and `available_at=now()` for that row; do not edit signed bodies or signature headers.
- Logs contain error categories, not event bodies, access tokens or provider responses. Raw bodies remain private database records for event processing.

## Validation performed locally

| Check | Result |
|---|---|
| Full existing backend plus initial bridge tests | 114 passed, 1 credential-gated real-AI skip |
| Final focused bridge tests, including capture reconciliation | 3 passed |
| Deno receiver tests with mocked external services | 11 passed |
| PostgreSQL permission/deduplication/lease/concurrency tests | 6 passed |
| Project creation/deployment-script tests with mocked account API | 3 passed |
| Deno check/lint | Passed |
| Backend Ruff and strict mypy | Passed; 75 source files typed |

The PostgreSQL tests used only the separate local `sentinel_supabase_check` database. They did not change the application database or its Alembic schema. Project-creation tests use mocked HTTP requests, not an actual Supabase account.

Repeat the new checks:

```bash
DENO_DIR=/workspace/.cache/deno /workspace/sentinel-tools/node_modules/.bin/deno test supabase/functions/paypal-webhook
SENTINEL_SUPABASE_TEST_DATABASE_URL=postgresql://sentinel:sentinel@127.0.0.1:5432/sentinel_supabase_check apps/api/.venv/bin/pytest supabase/tests
```

The existing API suite includes `tests/test_supabase_inbox.py`. No frontend or ML code changed. Live project creation, hosted Edge runtime behavior and real signed sandbox delivery remain blocked by missing account/provider credentials.
