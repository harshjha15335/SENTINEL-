# SENTINEL V2 — Render staging Blueprint handoff

Status: LOCAL REVIEW CANDIDATE; APPLICATION COMPATIBILITY BLOCKED; NOT APPROVED TO APPLY.
Date: 2026-11-11. Render is the only authorized hosting destination.

## Target and evidence

- Existing project: Sentinel, `prj-dbq48lon74is739m7nl0`.
- Workspace: My Workspace, `tea-d8gorhflk1mc73f4pmr0`.
- Environment: Staging (capitalization intentional).
- Owner reports Staging has 0 services, 0 environment groups and no deployed resources.
  This is owner-verified evidence, not an independent project inspection, and does not
  establish absence of a Blueprint or external deployment integration.
- Latest scoped workspace service inventory returned only an unrelated meeting-intelligence
  service. No existing hosting resources were modified.
- `deploy/render-staging.yaml` is the intended staging path. Root `render.yaml` remains a
  legacy demo manifest, now manual-only; do not use it as this staging deployment.
- The name-based projects/environments mapping expresses the intended placement. It does
  not encode an immutable project ID. Before approval, the actual Render plan must identify
  the existing project/environment, not create a similarly named project. Stop on mismatch.

## Configuration and functionality

One paid Docker web service builds the existing multi-stage Dockerfile: React production
assets are served by FastAPI on the same origin. Existing supervisor starts the API and
pipeline worker; one service instance preserves the singleton contract. No UI, backend,
models, migrations, dependency pins or Dockerfile were changed by this preparation.

PostgreSQL 16 matches compose and current CI. Database evidence storage persists across
container replacement; no separate disk, Redis, frontend host or paid AI service is added.
The service and database are proposed in Singapore, subject to owner/availability approval.
The application security profile must be `production` even though the Render environment
is Staging: current Settings rejects hosted deployments with another profile. This does
not enable live payments. PayPal is fixture, paid AI is `none`, refund execution and webhook
fixture ingress are false; no PayPal/AI/Supabase credentials are requested or supplied.
Provider-dependent functionality is intentionally unavailable in this initial mode; existing
implementation is preserved, not validated against live providers.

Auto deployment uses `autoDeployTrigger: 'off'`. Blueprint previews are explicitly off;
independent service preview generation is omitted (disabled per current specification).
Blueprint Auto Sync is NOT a YAML setting. Any future Blueprint creation must explicitly
use `autoSync: false`; verify it stays false before every manual sync. Disabling service
auto-deploy does not stop a manual Blueprint application from provisioning/building/deploying.

Migrations are operator-controlled through the pre-deploy command, pinned to reviewed head
`d105a4143283`; runtime auto-migration and automatic demo loading are disabled. No migrations
were run in this preparation. Seed users once after authorized deployment through private
operator input, never persistent generated seed-password variables. Existing passwords must
remain unchanged on restart; never use `--rotate-passwords` as a bootstrap retry.

## Published monthly estimate, retrieved 2026-11-11

| Resource | Proposed plan | Monthly USD |
| --- | --- | ---: |
| Web, 1 CPU / 2 GB RAM, one instance | 1c-2g | 25.00 |
| PostgreSQL, 0.5 CPU / 1 GB RAM | 0.5c-1g | 19.00 |
| Database storage, explicitly 1 GB | 0.30/GB-month | 0.30 |
| Base total | | 44.30 |

The measured historical application profiles peaked near 600 MiB, so a 512 MB web plan is
not an adequate basis for this unchanged application. The 1 GB database is a conservative
staging candidate, not a hosted load-test result. A 256 MB database would reduce the base
estimate to $31.30/month but is not selected without capacity evidence.

Assumes a $0 Hobby workspace fee and included build/bandwidth allowances. The actual workspace
plan/quote/credit eligibility are not independently verified. A $25 Pro workspace fee would
bring this base to $69.30/month and exceed $50 for one month. Taxes, excess builds, bandwidth,
optional backups/retention, existing account usage and later storage growth may add charges.
Confirm the exact dashboard quote before approval. Do not enable automatic storage growth,
extra replicas, previews or workspace upgrades as part of this proposal.

$50 is a finite credit balance, not a monthly allowance: $44.30 leaves $5.70 after one nominal
month; approximately 34 days at a 30-day-month equivalent before extras. This is not a budget
cap or billing guarantee. Configure account alerts and an owner-approved stop/decommission
schedule before provisioning. Stopping the web service alone does not eliminate database or
storage charges. Do not delete a database without backup and explicit authorization.

## Verification performed

- Read current Render Blueprint spec, JSON Schema, compute plans, pricing, environment
  variable documentation, PostgreSQL connection reference and infrastructure-as-code guide.
- Corrected root manifest and staging manifest pass downloaded public JSON Schema.
- YAML/topology checks pass: disabled deploy/previews, one instance, colocated resources,
  Docker paths, database reference, PostgreSQL 16, private DB allowlist and no provider keys.
- Two existing offline Render contract tests pass under pytest.
- Loaded literal staging variables through actual application Settings: fixture mode,
  secure hosted profile, database storage and disabled paid AI accepted.
- Verified migration head against Alembic graph without connecting to a database.
- Offline probe with an explicitly simulated healthy DB/pipeline correctly remained NOT READY
  because Supabase bridge is absent. This is not a live database or hosted health result.
- Runtime database connection arguments remain verify-full with an existing CA bundle.
- Render CLI is not installed: no platform-side Blueprint validation was performed.
- Full 508-test application suite was NOT rerun for configuration-only changes. Earlier
  508 passes/1 skipped remain historical evidence at the preceding remediation checkpoint.

## Application compatibility blockers — do not apply

1. Hosted readiness unconditionally requires `supabase_bridge`, including PayPal fixture mode.
   Supervisor starts that bridge only when a Supabase URL is supplied. This proposal deliberately
   supplies none, so /api/v1/ready cannot succeed. Do not fake heartbeats, disable hosted mode,
   disable worker readiness or switch the health check to liveness to conceal this.
   A separately scoped compatibility correction should make bridge requirements reflect actual
   configured integrations in fixture-only staging while retaining pipeline freshness and all
   genuine-provider safeguards. It needs review and regression tests before deployment.
2. fromDatabase.connectionString uses the internal Render endpoint. Existing hosted DB code
   forces sslmode=verify-full. Current Render documentation says internal self-signed TLS
   endpoints do not support verify-ca/verify-full. The present mapping therefore fails the
   hosted TLS contract. Resolve before applying: prefer a verified external endpoint with
   bounded Render egress allowlisting and an explicitly approved two-phase Blueprint procedure
   (database first, then securely bind its external URL), or another reviewed supported trust
   design. Do not silently downgrade verification or allow unrestricted external DB access.
   The current manifest stays private-only and fail-closed until that decision/configuration
   correction is made; it is not a deployable workaround.
3. Actual ingress proxy IP/CIDR scope must be verified and securely supplied through
   SENTINEL_FORWARDED_ALLOW_IPS. Wildcard/unbounded trust is forbidden. Do not guess a CIDR.
4. Exact existing-project mapping, plans/region/quote/credit coverage and host acceptance
   remain unverified. Schema acceptance alone cannot establish them.

No backend/security code was changed to work around these blockers; this authorization covers
local Blueprint preparation. Resolve compatibility locally, obtain a new final commit and
rerun affected regressions before calling this ready for deployment.

## Exact gated deployment procedure (future only)

1. Close H02: verify Render Blueprint inventory, GitHub webhooks/Apps/Pages/environment
   triggers, and absence of Vercel/Cloudflare SENTINEL bindings. Do not use a test push/PR.
2. Resolve the compatibility blockers above; revise the Blueprint/procedure as necessary.
   Revalidate schema, application settings/TLS/readiness, proxy trust and migration/bootstrap
   behavior; run affected regressions. Stop if any gate fails.
3. Obtain explicit authorization for pushing only the corrected remediation branch and
   opening a draft PR into integration. Verify new CI against its actual head, review browser
   checks outside CI, then obtain separate integration/main merge approvals. No deploy dispatch.
4. Select the final full release SHA after review (a merge can change it). With separate
   publication approval, create a dedicated frozen Git release branch at exactly that SHA;
   never let this ref follow main. Verify remote ref, source files and local commit agree.
   Its intended name is release/sentinel-v2-staging-approved; it has NOT been created.
   A branch declaration is not an immutable SHA pin: freeze it and recheck before each operation.
5. Approve the concrete staging cost, credit coverage, duration/alerts, backup and rollback
   plan. Obtain explicit authorization to CREATE a Blueprint and plan only. On creation use
   the canonical GitHub repo, confirmed workspace, frozen approved ref, the final staging
   Blueprint path and autoSync=false. Nothing in this document authorizes that API call.
6. Inspect the planned sync before APPLY approval: existing project ID must be
   prj-dbq48lon74is739m7nl0, environment Staging, exact approved source SHA, Auto Sync off,
   no previews, one intended web service and one intended database, no unrelated resources,
   no extra projects, replacements/deletions or unexpected costs. If the creation surface
   cannot target the existing project, stop and use a supported verified placement flow.
   Do not automatically adopt or modify unrelated resources to make the plan pass.
7. Resolve secret inputs privately. Never paste DB URLs/passwords in chat. Verify only
   fixture/none provider settings and bounded proxy trust; no AI/PayPal keys, no inherited
   env group enabling integrations. Stop if the final plan or remote ref changed.
8. Obtain explicit approval of this exact sync, SHA and cost BEFORE approving/applying it.
   If TLS resolution uses two phases, each phase needs a concrete reviewed plan/approval;
   preserve autoSync=false throughout. Provisioning/application may begin billing and deploy.
9. Verify actual build/deploy SHA, database TLS identity, migration revision, schema and
   genuine configured worker freshness. Require /api/v1/ready success; never substitute a
   static screenshot or liveness result. Bootstrap users once in a private operator session
   using getpass/secure one-off inputs, then run app.cli demo-load --if-empty if approved.
   Do not leave bootstrap passwords in service/group configuration or logs.
10. Exercise HTTPS, secure cookies, CSRF, roles/merchant boundaries, login/logout retry,
    approved desktop/mobile UI, checkout fixture labels, deterministic AI fallback, evidence
    upload/download persistence, review/refund-intent controls, investigations and pipeline
    handoff/restart. No real provider operations. Refresh/deep-link/back navigation too.
11. On failure, stop and report. Do not repeat paid builds, resize, weaken checks or rerun
    migrations blindly. App rollback must use an approved immutable compatible SHA; database
    downgrade/deletion/restore needs separate backup and approval. Staging success does not
    authorize production deployment or provider activation.

## Outstanding H02 owner checklist

- Render: workspace-wide Blueprint inventory (including paused/pending first-sync entries)
  must show no active SENTINEL binding capable of applying pushes. Empty Staging does not
  settle this. Confirm no service/preview binding elsewhere in the intended workspace.
- GitHub repository: active webhooks/events, installed Apps/repository access, Pages source,
  environment deployment rules and push/PR/main-trigger behavior.
- Vercel and Cloudflare owner accounts: no SENTINEL project Git bindings or deployment hooks
  capable of automatic deployment. Only inspect; report any binding before changing it.
- Record account/project/repo/branch, behavior for branch push/draft PR/PR update/main merge,
  and redacted settings/date. Blocked APIs were not repeatedly retried.
- After safety evidence is complete, explicit publication approval is still required.

## Sources

- https://render.com/docs/blueprint-spec.md
- https://render.com/schema/render.yaml.json
- https://render.com/docs/compute-plans.md
- https://render.com/pricing.md
- https://render.com/docs/configure-environment-variables.md
- https://render.com/docs/postgresql-creating-connecting.md
- https://render.com/docs/infrastructure-as-code.md

CODE REMEDIATION: PRESERVED
BLUEPRINT SCHEMA: PASS
APPLICATION HOSTING COMPATIBILITY: BLOCKED
PUBLICATION: BLOCKED PENDING H02 AND APPROVAL
DEPLOYMENT APPROVAL: PENDING
No push, merge, Blueprint creation/application, hosting change, paid AI or credit consumption.
