# SENTINEL Session 8 report — 22 October 2026

The independently executable infrastructure work is implemented and tested. The system remains workspace-local except for the existing public Supabase receiver. Continuous public Python hosting, authenticated PayPal operation and real AI verification are **not complete**. No genuine payment, refund, dispute submission, paid provisioning, Git push or merge occurred.

## Git and preservation

- Checkout: `/workspace/SENTINEL-recovered`; branch: `feature/supabase-webhook`.
- Starting commit: `94cf67d1c9f60b2280fcbac019eb0ce86f6df5ff`.
- Tested implementation commit: `212b354f4f43be9e82fa1dd630cfdff8f5bdc967`.
- The documentation delivery commit follows that implementation; its exact SHA is recorded in `/workspace/sentinel-session8/delivery.json` and the session's final response.
- Base backup created before implementation: `backup/session8-base-94cf67d-20261022`. Existing refs were not overwritten.
- Pre-sprint bundle `supabase-webhook-complete-20261022.bundle` verified with complete history.
- GitHub read-only branch inventory confirms public main at `aed5d5647d14b2f7fd29575b21487ead337c64b3` and Claude branch at `6cdd3d12f63ff42f1dee13db1145b7b69209bb5d`.
- The three earlier local integration commits `d3e3113`, `43122a4`, `94cf67d` and Session 8 commits are not on those GitHub branches. The recovered checkout's `origin` points to the other local clone; its remote-tracking refs are not evidence of GitHub publication.
- Original checkout remains at public main. Dedicated backup refs and a new full-history bundle preserve this sprint; see the delivery manifest for final verification and SHA-256.

No independent external backup destination is connected or verified. Download the new bundle and checksum file from the workspace artifacts, then on another machine run `sha256sum -c sentinel-session8-20261022.bundle.sha256`, `git bundle verify sentinel-session8-20261022.bundle`, and `git clone -b feature/supabase-webhook sentinel-session8-20261022.bundle SENTINEL-restored`. Confirm its HEAD against the delivery manifest. Do not overwrite an existing checkout. The Git bundle intentionally excludes credentials, database dumps and private evidence. Export those separately only through an approved private backup path.

## Implemented changes

### Readiness and startup

Readiness now compares the application's actual Alembic revision against the source migration head instead of accepting any version row. It rejects missing/mismatched schemas, absent/stale/degraded essential workers and future heartbeats. It distinguishes configured credentials from provider verification. Docker health now calls readiness rather than the process-only liveness route.

Container startup pins automatic upgrades to reviewed revision `8ab7245e13c0`, and `SENTINEL_AUTO_MIGRATE=false` supports operator-managed migration. `python -m app.cli check-schema` rejects incompatible schema before workers launch. There is no automatic downgrade. The Session 8 migration adds two nullable worker metadata fields and does not rewrite payment/evidence records. The independent Supabase inbox schema is unchanged.

`SENTINEL_HOSTED_DEPLOYMENT=true` rejects insecure hosted combinations: nonproduction environment, insecure cookies, local evidence storage, disabled worker-required readiness, and non-HTTPS CORS origins. Empty same-origin CORS is supported. Hosted supervisor startup rejects wildcard forwarded-proxy trust. Actual host proxy ranges/TLS still require deployment verification.

### Operator visibility

The new `/operations` screen is administrator-only, with loading, error, empty and stale states. Its typed API separates merchant event reconciliation, scoring and investigations, with origin-specific counts. It reports worker heartbeat freshness, failures, last successful work, exhausted events, database-backed evidence counts/bytes and provider configuration/recorded activity. Idle polling does not change last-success time.

The existing bridge samples private Supabase metrics every 30 seconds. Only installation administrators whose merchant matches `SENTINEL_OPERATIONS_INBOX_MERCHANT_ID` see global inbox origin/state aggregates. Other tenant administrators see no global inbox snapshot. Snapshots older than 90 seconds are stale. No provider IDs, raw bodies, evidence text or credential values are returned. Metrics failure does not prevent delivery; freshness exposes an old snapshot. Responses are no-store. Global worker metadata is operational process information, not merchant webhook details.

The Settings screen no longer says investigations arrive in a future phase; it reads actual AI configuration and labels deterministic fallback.

### Isolated judge demonstration

A trusted CLI `python -m app.cli judge-demo` accepts a private `SENTINEL_JUDGE_PASSWORD` and creates a separate DEMO tenant. Its viewer can explore generated payments, risk/SHAP, a prepared HIGH case, deterministic investigation, an explicitly synthetic unverified attachment, private PDF packet and pending internal approval. `/demo` guides that viewer through the prepared material. The authenticated scenario locator returns no scenario outside that tenant.

The internal curator's random password is discarded and no administrator is created for public access. Repeated setup keeps existing material and password; conflicts fail instead of overwriting a merchant identity. All generated transactions remain SYNTHETIC_DEMO. The attachment is uploaded through the existing evidence service, remains unverified and says it is not payment/delivery proof. Viewer mutations are denied by existing server authorization. The guide does not claim genuine PayPal or AI execution.

Existing investigation, evidence, packet and approval systems are reused. No model artifact, threshold, serving feature or frozen benchmark was changed. Historical synthetic precision stays 28.2%: 122 false positives among 170 HIGH flags. That supports human review, not autonomous financial action.

## Cloud network and providers

Current draft metadata lists exact PayPal certificate hosts `api.sandbox.paypal.com`, `api.paypal.com`, `api-m.paypal.com`, in addition to the existing sandbox REST host. Current requests pass CONNECT and TLS verification. The three certificate-host roots returned upstream 406/404/406; sandbox REST root returned upstream Cloudflare 403. These establish proxy/upstream reachability, not authentication or payment verification. Local DNS did not resolve the names; supported proxied requests still succeeded. Independent direct TCP/TLS stages were not measured.

This session did not publish or broaden cloud networking. Startup instructions were updated in the saved draft; review/save and publish are required to retain the configuration/snapshot for later tasks. No fresh-task restoration claim is made. The activation event that enabled current certificate-host access is not independently known.

A separate sandbox OAuth credential check through the actual gateway failed AUTHENTICATION, with no order/capture/refund calls. Secure runtime credentials or their delivery binding require correction; Edge-secret presence does not prove the Python binding works. No usable real AI key/model configuration is available, and the provider-backed AI test is skipped. See PROVIDER_VERIFICATION.md.

## Hosting and costs

Selected prepared architecture: one non-root Docker service running API/frontend + supervised pipeline/bridge, a separate persistent application PostgreSQL database with private evidence bytes, and the existing Supabase receipt inbox. No new public application URL exists.

`deploy/render-continuous.yaml` is a review-only starter service/basic-256mb database proposal in Singapore, auto-deploy disabled, reviewed migration target and hosted security checks enabled. No account access or cost authorization is available. Official Render/Railway/Supabase/Codespaces pricing/documentation pages were blocked by CONNECT policy. Current prices, memory suitability, backup guarantees, free-tier sleep/expiry behavior and account eligibility could not be verified. **No numerical current quote is claimed.** Obtain an official regional compute/database/storage/backups/egress/tax quote and explicit user approval before applying any billable plan. See HOSTING_READINESS.md for comparison and concrete deployment procedure.

The official hackathon URL supplied by the user is also blocked. Its rules and supplied November 12 deadline have not been independently confirmed.

## Runtime and Supabase

The retained startup helper starts PostgreSQL, applies the reviewed head and supervises the recovered application. Current local readiness returned HTTP 200, schema `8ab7245e13c0`, pipeline ok and Supabase bridge ok. Both workers had fresh HEALTHY heartbeats after a full supervisor restart. No successful genuine bridge task is recorded; zero processed tasks in that normal worker is accurate because genuine events are absent.

Existing public receiver:

`https://cfslzvvdjxstpupkqbpw.supabase.co/functions/v1/paypal-webhook`

It remains ACTIVE version 4, with PayPal verification and JWT check disabled for the callback. Public GET returned 200 and unsigned POST 400. The receiver source was unchanged; prior compiled-runtime compatibility evidence remains applicable. The function was not redeployed. All three PayPal Edge secret names are present.

Hosted inbox after the second explicit fixture run: **4 SIMULATED PROCESSED, 2 SIMULATED DEAD, 0 genuine events**. The two terminal fixtures deliberately have invalid fixture HMAC authentication. They are retained as labelled evidence. No genuine record was reset, mutated or relabelled for testing.

## Integration verification

The second hosted fixture test used the actual hosted private inbox, an explicitly local receiver with injected PayPal verification, isolated application database, HTTP bridge, unchanged model and durable scoring worker. It produced one HIGH assessment and exactly one case. It exercised duplicates, abandoned lease reclamation, real local API outage/restart, stale ownership rejection, out-of-order status and terminal invalid fixture authentication. PayPal calls: zero.

A new backend transport-loss test lets FastAPI commit a receipt, loses its HTTP response, then retries and verifies exactly one local event/job/case. Existing tests cover conflicting event payloads, wrong tokens, lease expiration, simulated/genuine isolation, retry exhaustion and generic 200 responses without durable proof. Supabase PROCESSED still means durable API acceptance, independently of reconciliation/scoring/investigation results.

## Security, evidence and recovery

Existing suite checks sessions, CSRF, logout, roles, tenant isolation, audit constraints, signature verification, private evidence download, type/size/PDF validation, checksum integrity and fixture-route production rejection. Supabase SQL tests check RLS and service-only grants. New operations tests verify viewer/analyst denial and operator/merchant scope. A literal scan compared changed source with available private credentials without printing values; no matches found. Credentials, evidence bytes and dumps are outside Git.

The app's rate limiter remains process-local. Proxy trust defaults to loopback, without a wildcard. Public-host HTTPS, forwarded-header behavior and managed backups have not been tested because the public application is not deployed. No dependency vulnerability scan, antivirus guarantee or full disaster recovery guarantee is claimed.

A full supervisor restart preserved authenticated admin/viewer sessions and byte-identical judge attachment/packet downloads. A new mode-600 PostgreSQL dump restored into disposable database `sentinel_restore_s8_2a597da4`; 18,108 transactions, 343 cases and all 14 stored evidence/packet blobs matched. The dump includes synthetic and browser-test records; these counts are snapshot observations, not real merchant volume. Managed backup schedules/retention/PITR remain unverified.

## Actual validation results

| Check | Result |
|---|---|
| Full backend, final source | **134 passed, 1 real-AI skip** |
| ML, unchanged served artifacts | **7 passed** |
| Frontend Vitest | **29 passed** |
| Browser desktop/mobile including operations/judge and axe | **12 passed** |
| Deno receiver | **11 passed** |
| Supabase SQL/deployment with dedicated local DB configured | **12 passed** |
| Backend Ruff/format and strict mypy | Passed; 86 application source files typed |
| Frontend TypeScript/ESLint/production build | Passed |
| Contract generation | Passed; typed operations and judge schemas regenerated |
| Additive migration upgrade/parent downgrade/upgrade and drift | Passed on disposable database |
| Non-root container startup/API/UI/session/pipeline | Passed; UID 10001, readiness health check |
| Full supervisor session/evidence restart | Passed |
| New private backup separate-DB restore | Passed |
| Actual hosted SIMULATED lifecycle | Passed; zero PayPal calls |

An initial SQL run omitted the isolated test DB variable and reported 4 passed/8 skipped; the corrected run passed all 12. Initial lint/type errors during implementation were corrected; final checks pass. No unresolved local test failure remains. The skipped AI test and failed external OAuth check are distinct from these passing local checks.

Container image: `sha256:0be12314acde659e4fad3c67bc2222cfcb68678bf9b37c48a7fbc30553fd615e`. The smoke intentionally omitted Supabase in its disposable application DB to avoid routing genuine receipts into a test database; the actual hosted bridge was validated separately. Later changes were tests, examples and documentation, without changes to the image's application implementation.

## Runtime variable names

Core: `SENTINEL_DATABASE_URL`, `SENTINEL_PAYPAL_MODE`, `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET`, `SENTINEL_PAYPAL_WEBHOOK_ID`, `SENTINEL_SUPABASE_URL`, `SENTINEL_SUPABASE_SERVICE_ROLE_KEY`, optional `SENTINEL_BRIDGE_API_URL`.

Hosted: `SENTINEL_HOSTED_DEPLOYMENT`, `SENTINEL_ENVIRONMENT`, `SENTINEL_COOKIE_SECURE`, `SENTINEL_CORS_ORIGINS`, `SENTINEL_STORAGE_BACKEND`, `SENTINEL_REQUIRE_WORKERS_READY`, `SENTINEL_FORWARDED_ALLOW_IPS`, `HOST`, `PORT`, `SENTINEL_AUTO_MIGRATE`, `SENTINEL_MIGRATION_TARGET`.

Optional operations/demo/AI: `SENTINEL_OPERATIONS_INBOX_MERCHANT_ID`, `SENTINEL_JUDGE_PASSWORD`, `SENTINEL_AI_PROVIDER`, `SENTINEL_AI_MODEL`, `SENTINEL_AI_API_KEY`. A Supabase personal access token is administrative, not a bridge runtime requirement. Never place service-role credentials in browser variables. Old `SENTINEL_INVESTIGATION_*` names are not application settings.

## Next five tasks, in priority order

1. Download and independently verify the final Git bundle/checksum outside this workspace. Obtain separate authorization for source publication when needed; no push is implied.
2. Confirm a suitable host's current quote/account resources, obtain cost approval, deploy the prepared continuous service/database, and verify the real HTTPS application URL.
3. Correct the secure sandbox OAuth credentials/binding and repeat only the nonfinancial authentication check. Genuine payment/refund/provider-event testing remains separately restricted.
4. Configure a supported real AI provider/model/key securely and authorize a bounded, case-scoped provider verification run; retain deterministic fallback meanwhile.
5. Complete host-specific proxy/cookie checks, scheduled backups/restore, monitoring and private judge access. Only after the hosted path is stable proceed to approval-protected refund execution, disputes, unrecovered Policy Lab/transparency/monitoring and network analytics.

## Evidence locations

Machine-readable logs and results: `/workspace/sentinel-session8/` (`backend-final.log`, `web-*.log`, `browser.log`, `receiver.log`, `supabase-final.log`, `migration-roundtrip.log`, `container-smoke.json`, `runtime-verification.json`, `backup-restore.json`, `connectivity.json`, `paypal-oauth-check.json`, `cloud-verification.json`, `hosted-fixture/result.json`). Private credentials, dumps and browser traces are not public report attachments. Final preservation information is in `delivery.json` and the bundle verification log.
