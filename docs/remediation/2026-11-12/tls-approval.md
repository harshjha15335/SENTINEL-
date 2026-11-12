# Approved synthetic Render staging TLS policy — 12 November 2026

Authorization update: the subsequent autonomous release prompt conditionally
supersedes the original no-publication/no-deployment restriction. H02, exact-source
Docker/CI, reviewed plan and verified credit/budget gates still apply. No new TLS
policy exception is authorized or needed. See autonomous-release.md.

Original record: the owner explicitly approved proceeding with the narrowly scoped internal PostgreSQL
TLS exception in the uploaded instruction titled “Approve Scoped Render Staging TLS
and Finalize Merge Candidate.” This is security-policy approval only, not approval to
publish, merge, create/apply a Blueprint, provision services or spend credits.

The proposal preserved as `render-internal-tls-initial-proposal.patch` is HISTORICAL
REVIEW MATERIAL. It has been applied and hardened in runtime code; do not apply it
again. Source checkpoints remain available at `backup/render-tls-268adac` and the
unchanged earlier commits. The final source SHA is recorded in the delivery report.

The active policy defaults to verify_full. Explicit render_internal_staging requires:

- Hosted production SECURITY profile with deployment_stage=staging.
- The exact approved project and workspace IDs, fixture PayPal, no provider keys,
  no configured Supabase, AI none, no genuine refunds or webhook fixture ingress.
- Secure cookies, database evidence storage and required worker readiness.
- An exact owner-reviewed short internal dpg-* host, user/database sentinel_staging,
  normal 5432 port, a nonempty managed password, no query overrides except require,
  no CA override, and no ambient libpq routing/service/client-file settings.

The runtime and Alembic validate the EFFECTIVE connection URL. Arguments explicitly
pin host/port/database/user/password, require TLS and disable GSS negotiation. Schema
migrations and worker engines share the policy. Wrong, missing and contradictory
profiles fail closed. Unknown policy values are not accepted.

TLS require encrypts but does NOT authenticate the server's certificate or hostname.
Operator-supplied account/project/host settings are trust assertions, not provider
attestation or cryptographic proof. The owner must authenticate the actual resource,
region, account and database identity through Render when resources exist. Do not
populate the reviewed-host input merely by copying unreviewed configuration. No real
Render database host currently exists in this task.

The actual host remains a required sync:false input. Use database-first review and a
second manual sync of the SAME Blueprint after host review. Auto Sync must remain
false, automatic deploys/previews off. Do not use genuine data or enable providers
under this exception. Other hosted profiles retain certificate/hostname verification.

The new container acceptance workflow is build/test only, with a read-only GitHub
token, no Render secrets and no registry push. It is prepared, not executed remotely.
Local Docker capacity remains inadequate; fresh CI image acceptance is a merge gate.
