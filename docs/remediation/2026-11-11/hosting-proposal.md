# SENTINEL V2: manual fixture-hosting proposal — NOT APPLIED

Deployment approval: PENDING. No resources, configuration, provider calls or paid usage are authorized by this document. Do not apply `render.yaml` or `deploy/render-continuous.yaml` unchanged.

## Source and release control

Use the exact remediation commit recorded in the final external report and `git rev-parse HEAD`, after its regression evidence passes independent review. A resolved full-SHA specification accompanies that report; branch names alone are not release pins. Keep PR #2 and main unchanged. No push, merge, PR update, account configuration or deployment is part of this task.

Render workspace already confirmed by owner: My Workspace (`tea-d8gorhflk1mc73f4pmr0`). User supplied project URL: https://dashboard.render.com/project/prj-dbq48lon74is739m7nl0 . Project membership/resources are UNVERIFIED: connector lacks project reads and the dashboard host was blocked by the environment proxy. Do not infer that the project is empty, belongs to this workspace or has a deployment binding. Identify and verify the project before any later provisioning proposal is approved. The observed unrelated meeting-intelligence service must remain untouched.

H02 remains OPEN: Vercel project read returns 403 for team `team_LiuXG8wkcqrVQNMjIX6aNPDB`; Cloudflare account bindings are unavailable. GitHub main reports protected=false and visible rulesets are empty. Detailed protection read is 403, and deployment/environment/Pages/webhook endpoints are not exposed by the connector. Source workflows are reviewed, but external Git bindings and environment protection must be verified by the owner.

## Candidate architecture and priced choices

One Docker service for same-origin API + compiled SPA + existing supervised worker, and one dedicated managed PostgreSQL database in the same approved region. No additional worker, cache, disk, domain or paid AI service is proposed. Use database-backed evidence storage.

Published estimates rechecked 2026-11-11, assuming Hobby workspace $0 and 1 GB PostgreSQL storage at $0.30/month:

| Candidate | Web | Database | Storage | Total/month | $50 runway (30-day model) |
|---|---:|---:|---:|---:|---:|
| Lean, conditional on DB capacity | 2 GB / 1 CPU $25 | 256 MB $6 | $0.30 | $31.30 | 47.9 days |
| More DB headroom, still unvalidated | 2 GB / 1 CPU $25 | 1 GB $19 | $0.30 | $44.30 | 33.9 days |

Neither is a purchase approval or hosted capacity certification. Pro workspace would add $25/month. Excludes egress, build overages, taxes, backup/add-on charges and other account usage. $50 balance/expiry 2027-11-01 is user-confirmed, not independently verified billing evidence. Credit eligibility, payment-method/overage policy and spending controls must be checked by the owner. No hard spending cap is assumed. 4 GB web at $85/month is not justified within this one-month budget. Free PostgreSQL expires after 30 days and is not durable hosting.

Keep credits unused until code and release controls are accepted. A static review artifact costs no incremental backend compute, but cannot provide operational authentication or writes. The smallest DB that passes measured workload is preferable; choosing the 256 MB database without that evidence is not recommended. Prior fresh API/worker RSS measurements are separate processes and not a whole-container capacity proof. 512 MB web has no verified headroom.

## Required environment review (values supplied privately, never committed)

| Setting | Proposed acceptance value / gate |
|---|---|
| Source revision | Exact full SHA in final external proposal; manual deploy that SHA |
| Automatic deployment | Off; verify actual service setting and all Git-provider bindings |
| Environment | `SENTINEL_ENVIRONMENT=production` |
| Hosted safeguards | `SENTINEL_HOSTED_DEPLOYMENT=true` |
| API bind | `HOST=0.0.0.0`; use provider PORT |
| Web distribution | Docker-built distribution from pinned source |
| PayPal mode | `SENTINEL_PAYPAL_MODE=fixture`; no PayPal credentials required |
| AI | `SENTINEL_AI_PROVIDER=none`; no AI key or paid model required |
| Refund execution | `SENTINEL_REFUND_EXECUTION_ENABLED=false` |
| Evidence storage | `SENTINEL_STORAGE_BACKEND=database` |
| Sessions | `SENTINEL_COOKIE_SECURE=true`; verify HTTPS and cookie attributes |
| CORS | `SENTINEL_CORS_ORIGINS=[]` for same origin |
| Proxy trust | `SENTINEL_FORWARDED_ALLOW_IPS` only owner/provider-verified bounded ingress IPs/CIDRs; never wildcard |
| Database | Dedicated provider endpoint; least privilege; verify-full TLS and matching trusted certificate; do not weaken verification to make internal DNS work |
| DB trust | Approved CA bundle/`SENTINEL_DATABASE_SSL_ROOT_CERT` if required |
| Migrations | `SENTINEL_AUTO_MIGRATE=false`; approved one-off migration to reviewed target d105a4143283; schema check before startup |
| Worker readiness | `SENTINEL_REQUIRE_WORKERS_READY=true`; verify fresh active-worker heartbeat |
| Supabase bridge | Unset unless separately required and approved; do not reuse operational credentials |
| Bootstrap | One-off private fixture identities; do not retain seed passwords in permanent runtime |
| Demo autoload | Off by default; isolated synthetic seed only through an approved one-off command |
| Logging | No cookies/tokens, upload contents, provider credentials or sensitive exception payloads; retain correlation IDs |
| Upload intake | New pre-authentication/file/aggregate limits; verify edge and app limits together |
| Sandbox callbacks | Not needed in fixture mode; any later sandbox enablement requires explicit public HTTPS return/cancel URLs and separate approval |

Current repo manifests stay unchanged as historical proposals. This document is the review artifact, not deployable infrastructure-as-code.

## Migration, rollout and rollback

1. Owner approves exact source, project/workspace, prices, credit terms and protected fixture acceptance scope.
2. Establish a recoverable database backup and demonstrate an isolated restore before any migration on an existing database. Fresh dedicated DB creation/migration still requires approval.
3. Run the explicit reviewed migration once, then check schema. Do not auto-downgrade or assume a binary rollback reverses database changes.
4. Deploy the approved immutable candidate manually. The old pipeline holds advisory lock 7682346; replacement pipeline stays in interruptible standby without spending supervisor crash retries or reporting its own success. Global readiness requires a fresh actual active-worker heartbeat.
5. On graceful shutdown, finish the current durable job, release lock and let standby acquire it. Abrupt owner death relies on PostgreSQL session lock release; job retries retain existing idempotency/transaction semantics.
6. Local overlap, SIGTERM, SIGKILL and waiting-shutdown regressions are required evidence. They do not prove hosted routing, provider termination timing or complete process restart behavior. Verify a budgeted hosted rollout and rollback later; keep H01's hosted acceptance gate open until then.
7. Stop rollout on stale worker heartbeat, job loss/duplication, auth failure, TLS mismatch, OOM, error growth or unexpected provider egress. Do not declare waiting state healthy by inventing a heartbeat.
8. Roll back to the prior approved immutable artifact through an explicit owner-approved action. For the first deployment, stop acceptance and preserve evidence if no prior release exists. Reconcile durable jobs before reattempting. Do not reverse financial effects or database migrations blindly.

## Capacity, cost and stop/teardown gates

Before approval, set a time-limited fixture test, concurrency/request limits, latency/error/queue thresholds and resource/cost alarms. Capture whole-container memory including model + API + worker, DB connections, CPU, p95 latency and peak queue age. No capacity verdict follows from static DB size or separate RSS values alone.

Plan a budget review before the credit reserve is exhausted. Stopping/suspending a web service must not be assumed to stop database/storage charges. Teardown is a separate explicit approval: verify dedicated resource IDs, export approved data/evidence, confirm restore requirements, then remove only those dedicated resources and verify billing cessation. Never delete the unrelated service or a shared database.

## Owner checks still needed

- Render project URL belongs to intended workspace; project/service/environment/Blueprint relationships and permissions.
- Actual credit balance, eligible charges, workspace fee, quote, overage controls and region.
- Vercel and Cloudflare linked repos/branches/production triggers/previews/protection, or authoritative absence.
- GitHub Pages source, deployment environments/approvals, webhooks and installed app bindings; consider required reviews/checks on currently unprotected main.
- Hosted TLS/proxy/cookies, worker rollout/rollback, capacity and protected application acceptance.

No genuine sandbox payment/webhook/refund or paid inference is included in initial fixture acceptance. Live-provider validation remains NOT EXECUTED and separately approval-dependent.
