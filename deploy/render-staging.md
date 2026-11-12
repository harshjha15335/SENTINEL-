> Latest release authorization (12 November 2026): owner-verified Blueprint,
> webhook and empty-Staging checks are accepted; remaining uninspected integrations
> are acknowledged residual risk. Earlier blanket H02 publication blocks below are
> historical and superseded by docs/remediation/2026-11-12/owner-release-evidence.md.
> Current CI/Docker/source-preservation and billing/plan gates still apply.

# SENTINEL V2 — Approved Render synthetic staging TLS handoff

Current authorization: the owner's later “AUTONOMOUS FINAL INTEGRATION, REMEDIATION,
MAIN MERGE & RENDER DEPLOYMENT” prompt conditionally authorizes branch publication,
reviewed merges and Render staging provisioning. Routine reconfirmation is not
required. Publication still requires H02 evidence; main requires passing exact-source
Docker/CI acceptance; provisioning requires verified eligible credits, an unambiguous
reviewed plan and reliable budget controls. These gates remain unresolved. Genuine
payments, paid AI, out-of-pocket charges and unrelated resource mutations are excluded.
The earlier narrower TLS authorization remains historical below; it no longer defines
the entire action scope. See docs/remediation/2026-11-12/autonomous-release.md.

## Source and approval

Starting candidate: 268adacaa0958a7bb5df6cdc576ee2d8e77bbfae.
Preserved checkpoint: backup/render-tls-268adac. Earlier checkpoints/integration/main
were not rewritten. The final full SHA is in the external delivery report.

The initial proposal was reviewed completely, applied and hardened. It is archived
at docs/remediation/2026-11-12/render-internal-tls-initial-proposal.patch; DO NOT apply
it again. The approval record is alongside it in tls-approval.md.

## Active TLS policy

Default hosted SQLAlchemy/Alembic/worker behavior remains verify-full with a trusted
CA bundle. No global SSL-disable option exists. The exception must be explicitly
selected as render_internal_staging and passes all of these gates:

- Hosted production SECURITY profile, separate deployment_stage=staging.
- Exact approved project prj-dbq48lon74is739m7nl0 and workspace tea-d8gorhflk1mc73f4pmr0.
- Fixture PayPal, AI none, no PayPal/AI/webhook credentials, no configured Supabase,
  no real refunds and no fixture webhook ingress.
- Secure cookies, database evidence storage and mandatory worker readiness.
- Exact owner-reviewed short dpg-* internal host, database/user sentinel_staging,
  port 5432, nonempty managed password, no CA override or URL query redirects.
- Only absent sslmode or explicit require is accepted in the exception's URL;
  all other modes/extra connection query keys fail closed.
- Ambient libpq routing, service, password-file and TLS overrides are rejected.

The effective migration URL is validated, including Alembic's context override.
Host/port/database/user/password are explicitly pinned in connect_args, sslmode is
require and gssencmode is disable to mandate TLS rather than plaintext fallback or
another negotiation. Production stage, wrong IDs, provider-enabled settings and
unexpected endpoints fail closed before connection. Configuration errors suppress
input values so a failed guard does not print database passwords.

`require` encrypts but DOES NOT authenticate the server certificate or hostname.
This is the explicitly accepted synthetic-staging trade-off. These configuration
values express operator-reviewed trust; they are NOT provider attestation. The
actual account/project/region/host/user/database must still be authenticated and
reviewed through Render after resources exist. Do not copy an unreviewed host into
the reviewed-host input merely to make validation pass. No actual Render database
has been created here. Genuine data and production must retain strict verification.

## Readiness and application integrity

The earlier mode-aware readiness correction remains: fixture-only staging requires
DB, exact schema and fresh healthy pipeline, not a fabricated Supabase heartbeat.
Configured and sandbox integrations retain genuine required bridge/configuration
checks. Shutdown/crash/restart/handoff safeguards remain intact. Provider verification
is explicitly not inferred from readiness. Approved UI, fraud engine/model artifacts,
auth/logout/upload/callback/payment controls, dependencies and migration REVISIONS
are unchanged. Only migration CONNECTION configuration changed to validate overrides.

## Blueprints and cost

Root render.yaml mirrors deploy/render-staging.yaml. They define ONE intended
application and ONE PostgreSQL 16 database in existing Sentinel/Staging. Do not
create two Blueprints from the mirrors. deploy/render-staging-database.yaml is a
first phase of that same manual Blueprint.

- 2 GB / 1 CPU application, one instance (1c-2g): $25/month published base.
- 1 GB / 0.5 CPU PostgreSQL (0.5c-1g): $19/month published base.
- Explicit 1 GB database storage: $0.30/month; private-only external allowlist.
- Total $44.30/month assuming $0 Hobby workspace fee and included allowances.
- Prior local sizing: 256 MB/.1 CPU p95 5.80 s; 1 GB/.5 CPU p95 0.74 s on four-reader
  fixture workload. No new evidence justifies downsizing. No cost was incurred here.
- $50 leaves $5.70 after a nominal month before extras; a seven-day acceptance trial
  is approximately $10.34 base, not a cap. Actual account/credit/fees/usage unverified.

Auto-deploy trigger off, previews off, no runtime auto-migration, paid AI/refunds off,
no provider secrets or persistent seed passwords in YAML. Pre-deploy migration stays
pinned to d105a4143283. Proxy trust and actual reviewed host are required manual inputs.
Blueprint Auto Sync is not a YAML field: create with autoSync=false and verify it
before each manual sync. Name-based project placement must match the EXISTING project
ID in the actual plan, not a duplicate name. All three files pass public JSON Schema.
Render CLI/platform-side validation and actual resource binding remain unverified.

## Fresh local verification

597 passed, one live-AI test skipped: backend 445, frontend 53, ML 7, auxiliary 34,
operational browser 34, static browser 24. 63 new security cases above 534; targeted
74-test runs are not double-counted. Default production verification, disallowed
profiles/endpoints, libpq overrides, actual migration URL override, secret-safe
errors, worker connection policy and real no-plaintext driver behavior are covered.
Existing incorrect-CA/hostname and TLS refusal tests remain unchanged and pass.

Backend lint/format/typing, frontend lint/typing, ML checks, production/portable/static
builds, OpenAPI/generated-TypeScript parity, disposable migrations/schema, keyboard,
security and production isolation pass. Frontend tests ran with one worker without
changing assertions/timeouts. 51 rendered visual checks report no layout/accessibility/
page defects. No genuine provider was called and no credential was externally tested.
A separate offline configuration probe confirms genuine-mode production settings
still use verify-full while rejecting this staging exception.

## Docker capacity and exact CI acceptance

The local filesystem is approximately 8 GB total with only about 0.15-0.2 GB free;
Docker uses VFS and has zero reclaimable build cache. Prior real build and startup
attempts exhausted storage; those logs were retained. No unrelated files, source
worktrees or recovery backups were deleted in this task. No paid or remote build
environment was provisioned. Retrying unchanged capacity would risk the disposable
PostgreSQL server again; this task stops at preflight, not a claimed build pass.

Prepared .github/workflows/render-staging-container.yml:

- PR/main push/manual dispatch; contents:read only; no Render secrets, cloud API,
  deployment environment, registry push or token-write permission.
- Exact checkout SHA and clean tree required; at least 8 GiB free build space.
- Standard Dockerfile fresh build with source SHA label/fingerprint checks.
- Unique owned internal Docker network/volume; generated ephemeral credentials.
- Explicit no-TLS PostgreSQL rejection, self-signed encrypted staging acceptance,
  and default-production rejection of the untrusted certificate.
- Reviewed migrations, synthetic seed/load, actual API + worker boot, readiness,
  compiled UI/login/170-case smoke, genuine pg_stat_ssl sessions, crash recovery,
  graceful STOPPED and restart checks. Bootstrap secrets are temporary only.
- Cleanup restricted to invocation-owned fixtures/image; no broad prune or host cleanup.
- Retains build/startup/TLS summary artifacts even on failure.

The reproducible entrypoint is:

    python3 scripts/verify_render_staging_container.py \
      --expected-sha "$GITHUB_SHA" \
      --output "$RUNNER_TEMP/sentinel-staging-container"

The script/workflow pass syntax/lint/static YAML checks. Full container acceptance
is NOT executed locally or remotely. A PR can build GitHub's merge SHA; review the
reported exact SHA, not just the branch label. A fresh passing container job is a
merge gate after H02-cleared publication under the current conditional authorization. Do not dispatch the legacy
Image workflow on main if registry publication is not separately authorized.

## H02 and controlled release sequence

Owner read-only checks remain necessary; blocked external APIs were not retried:

1. Render workspace Blueprint inventory including paused/pending-first-sync entries,
   other SENTINEL services/previews and repo/ref bindings. Owner-verified empty Staging
   alone does not prove absence of automatic provisioning/deployment connections.
2. GitHub webhooks/events, installed Apps/repo access, Pages source, environments and
   behavior on fix-branch push, draft PR, PR update, main merge and successful-check completion.
3. Vercel/Cloudflare owner inventories proving no automatic SENTINEL Git/hook binding.
   Render-only policy does not disable existing external settings. No new configuration
   for either platform was prepared. Report discovered bindings before modifying them.

After H02 evidence establishes safety, the current autonomous authorization permits:

1. Push only the approved fix-branch SHA to the canonical GitHub URL, create one draft
   PR into integration/sentinel-v2-antigravity-20261111. Local origin is the recovery
   repo; do not use an unqualified push, all branches/tags, force or direct main push.
2. Verify fresh CI INCLUDING the new container acceptance at its actual source SHA;
   review all diffs and the browser coverage outside normal CI. Draft is not deployment
   protection. New workflow adds one CI job; existing manual publishers are unchanged.
3. Merge remediation into integration only after review and mandatory checks pass.
   Recheck PR #2 and merge to main only after every specified merge gate passes.
4. Freeze the actual approved post-merge release SHA/ref. Confirm account quote/credits,
   seven-day budget/alerts, backup/rollback and existing project placement.
5. Only with CREATE/PLAN authorization create ONE manual Blueprint, autoSync=false,
   using database-first path. Separately approve applying that reviewed DB plan.
6. Authenticate the created database/host/user/region binding, supply exact reviewed
   host privately, then manually plan the application phase of the SAME Blueprint.
   Require one retained DB plus one app, exact approved SHA and no unrelated changes;
   separately approve applying it. Do not create duplicate stacks or adopt unrelated services.
7. Verify deployed SHA, TLS/schema/workers, HTTPS/proxy/client identity/cookies/CSRF,
   roles/tenant boundaries, synthetic workflows, evidence persistence, approved UI/mobile
   and restart/handoff. Bootstrap users once privately. No genuine data/providers.

No hosted known-good rollback target exists yet. First-deploy failure: stop and
preserve DB/evidence. Later rollback uses an approved tested immutable source SHA
compatible with schema AND TLS/readiness policy. Do not automatically downgrade or
delete the database. Restore/delete/resize/repeated charged operations require separate
approval. A local Git recovery checkpoint is not proof of hosted rollback readiness.

TLS SECURITY POLICY: APPROVED AND IMPLEMENTED LOCALLY
LOCAL REGRESSIONS: 597 PASSED / 1 LIVE-AI SKIPPED
ACTUAL HOST BINDING: PENDING FUTURE RESOURCE CREATION/OWNER REVIEW
FRESH DOCKER ACCEPTANCE: BLOCKED LOCALLY; CI WORKFLOW PREPARED, NOT RUN
PUBLICATION / MAIN MERGE / STAGING DEPLOYMENT: BLOCKED; NOT AUTHORIZED
