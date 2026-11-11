# SENTINEL V2 — Render staging compatibility handoff

Review date: 12 November 2026 (Asia/Calcutta). LOCAL ONLY. No push, PR action,
merge, Blueprint creation/application, Render resource modification, genuine
PayPal/webhook operation, paid AI call or Render credit consumption.

## Source and checkpoint

Starting commit: `8993816840192e259cedc2e02809d455328a85ff` on
`fix/sentinel-v2-acceptance-blockers`. Preserved local checkpoint:
`backup/render-staging-8993816`. The exact final SHA is in the external final
report; this document is included in that commit, not a self-referencing SHA.
Existing GitHub integration/main refs were read again without modification.

## Root causes and readiness correction

Before editing, readiness required both pipeline and Supabase bridge for every
worker-gated deployment, while the supervisor only started a bridge when its raw
URL environment variable was present. The CLI readiness gate also hard-coded both
workers. That mismatch made intentionally unconfigured fixture staging impossible.
The old dependency graph and pre-edit behavior are retained in the review evidence.

Settings now validates complete Supabase URL/key pairs and trusted project-origin
shape. Partial/invalid configuration fails closed. A sandbox deployment, or ANY
configured Supabase integration, still requires a genuine healthy bridge. Fixture
mode with no Supabase requires PostgreSQL, exact schema and fresh HEALTHY pipeline;
it reports `not_required_fixture_mode` for the deliberately absent bridge. It does
not create a fake bridge heartbeat. Required sandbox configuration/credentials
cannot be replaced by an old healthy row. Provider verification remains explicitly
unverified by readiness; 200 is not proof of successful PayPal or paid AI access.

The supervisor refuses missing mandatory bridge configuration before child startup,
marks a configured bridge STARTING and marks a failed worker DEGRADED before restart.
An owning pipeline marks STOPPED before releasing its advisory lock on graceful
exit; standby never fabricates owner health. Abrupt failure is detected by the
supervisor; independent heartbeat freshness still has the existing 45-second bound.
The CLI only permits a bridge exemption with explicit --fixture-only, fixture mode,
absent configuration and the matching truthful API state; its default remains strict.

| Deployment | Required worker contract |
| --- | --- |
| Hosted fixture, no Supabase | Pipeline + DB + exact schema; no bridge |
| Fixture with complete Supabase configuration | Pipeline + healthy configured bridge + DB/schema |
| Sandbox with worker gate | Pipeline + genuine bridge/configuration, paired PayPal credentials + DB/schema |
| Partial/invalid Supabase settings | Configuration rejection; no ready claim |
| Worker missing/degraded/stopped/stale | Not ready; recovery requires fresh genuine HEALTHY heartbeat |

Fixture-only staging preserves UI, risk scoring, evidence, review and deterministic
investigation behavior. It does not verify genuine webhook delivery, actual PayPal
checkout/refund execution or paid AI. Refund execution and fixture webhook ingress
remain disabled. There is no live PayPal mode.

## PostgreSQL TLS decision — APPROVAL PENDING

Active hosted SQLAlchemy, Alembic and workers continue using verify-full. URL modes
cannot downgrade it. No generic disable-verification variable was added to active
runtime code. The unchanged default connection policy is exercised by real local
TLS/no-TLS/CA/hostname tests, migrations and genuine supervised worker connections.

Render documents self-signed internal database TLS that does not support verify-full.
The active internal Blueprint reference therefore remains intentionally non-deployable
under current security policy. Do not apply it merely because schema validation passes.

Option A (recommended for limited fixture staging, OWNER APPROVAL REQUIRED): private
same-region Render PostgreSQL with mandatory encrypted-only require, an exact
owner-reviewed short internal host, database/user, hosted staging/fixture/no-AI scope,
no genuine Supabase integration, no refund execution, no connection-query redirects
or explicit CA override. The material trade-off is lack of server certificate/hostname
authentication. Owner authentication of the Render account/resource binding does not
turn require into cryptographic server authentication.

An inert patch is provided at `deploy/approval-pending/render-internal-tls.patch`.
It proposes runtime and Blueprint changes but IS NOT APPLIED OR ACTIVATED. Syntax,
patch applicability and isolated offline scope probes pass (one allowed, 12 rejected).
That is not its full regression acceptance. Approving this exact security trade-off,
then applying/testing it in a new commit, remains necessary. Production defaults stay
strict; no actual internal host has yet been provisioned or approved.

Option B: retain verify-full with the actual external Render endpoint, trusted CA
chain and hostname, and bounded Render egress allowlisting. More setup/latency and
possible outbound usage; no dedicated IP purchase. Live endpoint/CA/network compatibility
cannot be established before resources exist. Never use unrestricted external DB
allowlists. This needs revised concrete configuration and reviewed plans, not an
unverified URL substitution.

## Blueprint configuration

Target existing Sentinel project `prj-dbq48lon74is739m7nl0`, My Workspace
`tea-d8gorhflk1mc73f4pmr0`, environment Staging. Owner verified 0 services,
0 environment groups and no deployed resources there. This does not prove absence
of Blueprints or external deployment bindings. Names in YAML express placement
intent, not an immutable project-ID guarantee: inspect the actual plan and stop
if it would create a duplicate project or touch unrelated resources.

Root `render.yaml` now mirrors `deploy/render-staging.yaml`; choose ONE Blueprint,
not two stacks. `deploy/render-staging-database.yaml` is a database-first phase of
that same future manual Blueprint, not authorization or a second database.

- One existing Docker application: built React served by FastAPI on one origin,
  supervised durable pipeline, one instance, plan 1c-2g, Singapore.
- PostgreSQL 16 (matching CI), plan 0.5c-1g, same region, explicit 1 GB disk,
  private-only `ipAllowList: []`.
- autoDeployTrigger off, no automatic previews; service preview generation omitted.
- Blueprint Auto Sync cannot be disabled in YAML: future creation MUST explicitly
  set autoSync=false and every manual plan must verify it remains false.
- Fixture PayPal, AI none, refunds false, webhook fixture ingress false; no provider
  credentials or persistent bootstrap passwords in configuration.
- Production security profile inside Render Staging: secure cookies, DB evidence
  storage, empty CORS list (same origin), worker readiness required.
- Exact reviewed migration d105a4143283 in pre-deploy command; runtime auto-migration
  and automatic demo loading off. Proxy trust is a mandatory owner-supplied bounded
  IP/CIDR input; never guess or use wildcard trust.

## Measured database sizing and cost

Both local limits were verified in cgroup memory.max/cpu.max. Same 9,051 synthetic
seed records, 24 new simulated scoring jobs, four concurrent authenticated readers
and 96 requests. No genuine providers. The API/worker ran outside the DATABASE limit;
this is database sizing, not a new whole-application memory profile. Shared disposable
PostgreSQL test infrastructure differs from a fresh managed Render instance; results
are local acceptance evidence, not a hosted latency guarantee.

| Metric | 256 MiB / 0.1 CPU | 1 GiB / 0.5 CPU |
| --- | ---: | ---: |
| Migration | 6.86 s | 4.36 s |
| Synthetic data load | 37.09 s | 14.09 s |
| p95 read response | 5796.91 ms | 742.51 ms |
| Maximum read response | 8699.42 ms | 843.45 ms |
| Peak sampled DB connections | 10 | 8 |
| Transactions after probe | 9075 | 9075 |
| Completed queued scoring jobs | 24 | 24 |
| Database bytes | 19577879 | 19512343 |
| New OOM events | 0 | 0 |
| Pre-set p95 target <= 2 seconds | FAIL | PASS |

The 256 MB plan remained functional and memory fit; its tested workload latency
failed the pre-set target. Do not claim it cannot run PostgreSQL or that memory
alone demands 1 GB. Retain 1 GB / 0.5 CPU for the four-reader staging scenario.
The 256 MB aggregate summary/logs survive; a harness filename collision overwrote
its raw per-sample array, disclosed in the evidence summary. No samples were invented.

Current published base monthly estimate (Hobby workspace fee assumed $0):
web $25 + PostgreSQL $19 + 1 GB database storage $0.30 = **$44.30/month**.
The rejected cheaper combination would be $31.30/month. $50 leaves $5.70 after
one nominal month before extras (about 34 days at a 30-day equivalent). A bounded
seven-day staging trial is approximately $10.34 base, not a quote or spending cap.
A $25 Pro workspace fee would make the total $69.30/month. Actual account plan,
credit coverage/expiry/eligibility, taxes, builds, bandwidth and other workspace usage
remain unverified; obtain the exact dashboard quote before approval. Do not upgrade
workspace, enable autoscaling/storage growth/replicas/previews or spend credits now.

The cgroup comparison used only a disposable LOCAL database container. Docker's
zero-valued update failed to clear limits, so the same local service was recreated
with its existing volume retained. Original unlimited resource settings, original
TLS settings and every database name were verified restored. No Render resource changed.

## Complete local acceptance

| Suite | Passed |
| --- | ---: |
| Backend | 382 |
| Frontend | 53 |
| ML | 7 |
| Auxiliary | 34 |
| Operational desktop/mobile browser | 34 |
| Static desktop/mobile browser | 24 |
| TOTAL | 534 |

One credential-gated live-AI test skipped; no live providers used. 26 new unique
regression cases over 508. Targeted reruns are not added again to this total.
Backend lint/format/typing, frontend lint/typing, ML lint/format, production/portable/
static builds, executable OpenAPI and generated TypeScript parity, offline Postman
validation, disposable migration/schema checks and production isolation pass.
51 visual checks report no layout, accessibility or page errors; keyboard and security
browser probes pass. Original test-function ASTs in extended files are unchanged.

A local actual entrypoint/supervisor run used the hosted security profile, current
source/build, strict verify-full and temporary locally trusted certificate/SANs.
Migration 2.92 seconds; ready after 10.46 seconds; genuine DB sessions TLS 1.3.
No Supabase heartbeat was fabricated. Killing the pipeline caused 503, then genuine
recovery; graceful shutdown persisted STOPPED; restart became ready. This is NOT a
Render certificate or public HTTPS/proxy verification result.

Fresh source integrity checks preserve approved frontend, financial controls,
auth/logout, callback validation, upload security, models, existing migrations,
Dockerfile, entrypoint, dependencies and contracts outside the targeted changes.
A real pending-job handoff probe again completed the job after owner death, with
one assessment/one attempt after duplicate enqueue and graceful lock release.

## Docker verification — BLOCKED BY LOCAL STORAGE

The full unchanged Dockerfile was actually attempted. The VFS-backed local Docker
filesystem exhausted space at COPY of package metadata, before a successful image
build. Retained-runtime source probes also failed: an unusable bind-mounted Alembic configuration (mapping not verified),
a test-harness HOME issue (corrected), then disk exhaustion during migration even
with copied current source. They are NOT successful fresh-image startup evidence.
The local supervised startup above establishes application behavior separately.

Do not mark Docker build/startup or Render staging as passed. Repeat a fresh full
build and disposable fixture startup in an adequately sized local workspace or,
after H02 and publication approval, the reviewed GitHub CI. Preserve logs and never
weaken tests/checks to work around capacity. Initial overlapping test/schema access
and disk-induced PostgreSQL failures were retained; final full suites ran after
recovery against separate disposable databases. Test assertions/timeouts were not weakened.
Unused local Docker images/build cache were removed during capacity recovery; Git checkpoints and existing data volumes were preserved. Task-created disposable databases were removed after evidence capture.
Generated dependencies were temporarily RAM-backed for capacity; source and delivery
artifacts remain in workspace. Recreate generated dependencies from pinned manifests
if the runtime restarts; this is not a source dependency change or transitive lock.

## Remaining H02 and authorization gates

Read-only owner evidence required; do not repeat blocked APIs or create test pushes:

1. Render workspace Blueprint inventory, including paused/pending first sync, and any
   SENTINEL service/preview binding elsewhere. Empty Staging alone is insufficient.
2. GitHub active webhooks/events, installed Apps/repo access, Pages source, environments
   and behavior on branch push/draft PR/PR update/main merge.
3. Owner Vercel/Cloudflare inventories: no SENTINEL Git binding or deploy hook capable
   of automatically publishing it. Policy permits only Render; no other deployment
   configurations were prepared. Report discovered bindings before changing them.
4. Record account/project/repo/ref/settings/date with secrets redacted. Actual plans,
   project mapping, proxy trust, credit coverage and public-host acceptance remain open.

Publishing is not authorized. Local origin is the recovery repo, so any later approved
push must explicitly target https://github.com/harshjha15335/SENTINEL-.git, only the
new fix branch and approved SHA; no all-branch/tag/force/main/integration push.
New draft PR base: integration/sentinel-v2-antigravity-20261111. Existing PR #2 remains
unchanged. Draft PR status does not disable external previews or CI.

## Exact staged procedure and rollback

1. Review readiness changes and the precise TLS trade-off. If internal require is
   approved, apply the inert patch LOCALLY, add required policy regressions, run full
   acceptance and record a new SHA. Otherwise prepare/verify strict external strategy.
2. Close H02. Obtain explicit fix-branch push/draft-PR approval, publish only approved
   source, verify fresh checks at that head (including Docker). Review coverage outside CI.
3. Separately approve remediation merge into integration, reverify PR #2, then separately
   approve main merge. Never treat old 8250671 checks as checks of this new candidate.
4. Select the final full approved release SHA AFTER merging; with explicit ref-publication
   approval, freeze a dedicated release branch at that SHA. It must not follow main.
5. Approve actual plans/credit/budget/duration/backup/rollback. With separate CREATE/PLAN
   approval, create one Blueprint with autoSync=false, correct repo/frozen ref, database-first
   path and confirmed workspace. Inspect placement in EXISTING prj-dbq48lon74is739m7nl0 / Staging.
   Stop on duplicate project, unrelated resources, changed source, unexpected charges or failed plan.
6. Obtain explicit approval of the database-only sync before applying it. This starts billing.
   Authenticate the created host/region/account binding. Review internal exact-host input, or
   external trusted endpoint and bounded egress ranges. Do not open unrestricted access.
7. Manually update the SAME Blueprint to the final reviewed app path/ref, keeping Auto Sync off.
   Review plan: existing intended DB retained, only one intended web service added, same approved
   SHA, no deletions/replacements/unrelated adoption. Supply inputs securely. Obtain explicit
   approval BEFORE approving/applying this second sync. No prototype placeholder is deployable.
8. Verify actual built/deployed SHA, schema, TLS policy, genuine required worker freshness,
   HTTPS/proxy/client-address behavior, secure cookies, CSRF, tenant/roles, evidence persistence,
   fixture checkout labels, scoring, investigations, review/refund-intent boundaries, mobile,
   logout/reload and worker handoff. Bootstrap users once with private one-off password input,
   never persistent seed secrets; demo-load --if-empty only as approved. No paid/real providers.
9. On failure stop and preserve evidence/database. No blind rebuild, resize, DB downgrade,
   secret logging or repeated charged operation. First deployment has no hosted known-good
   rollback target yet. Later app rollback uses an approved tested immutable SHA compatible
   with schema/TLS policy. Backup/restore/deletion needs separate approval; never revert an
   established database automatically. Source checkpoint 8993816 is recoverable locally,
   but its original fixture readiness blocker makes it an unvalidated hosted rollback target.
10. Successful Staging does not authorize production, paid AI or genuine PayPal activation.

READINESS BLOCKER: FIXED LOCALLY
RENDER INTERNAL TLS: APPROVAL-PENDING (inert patch; active strict default retained)
LOCAL REGRESSIONS: 534 PASSED / 1 LIVE-AI SKIPPED
FULL DOCKER BUILD/STARTUP: BLOCKED — LOCAL VFS DISK CAPACITY
PUBLICATION / MAIN MERGE / RENDER DEPLOYMENT: BLOCKED; NOT AUTHORIZED
