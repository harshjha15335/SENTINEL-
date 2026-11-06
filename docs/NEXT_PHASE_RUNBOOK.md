# Deployment, backup and recovery runbook

## Release preparation

1. Export and independently verify the Git bundle and checksum; local backup branches alone are not an off-environment backup. Obtain explicit source publication authorization if the host needs a Git branch.
2. Review `deploy/render-continuous.yaml` as a proposal only. Obtain an official current quote and account access, then explicit cost approval before any paid provisioning. No public application URL is claimed by a deployment file.
3. Use one non-root container initially with persistent application PostgreSQL, private database evidence and supervisor-managed API/pipeline/bridge. Supabase Edge Functions do not host this Python/XGBoost worker runtime.
4. Configure TLS/HTTPS, secure cookies, empty same-origin CORS or explicit HTTPS origins, and exact trusted proxy ranges. Hosted configuration rejects insecure settings and wildcard proxy trust. The process-local login limiter is not a shared multi-instance limiter.
5. Take a private backup. Review `d105a4143283` before migration. Never target the Supabase inbox with application Alembic commands.

## Migration/startup

From `apps/api`, run `.venv/bin/alembic upgrade d105a4143283`, then `.venv/bin/python -m app.cli check-schema`. The container performs only the reviewed configured target when `SENTINEL_AUTO_MIGRATE=true`; disable auto-upgrade for operator-managed releases. Start `python -m app.workers.supervisor`. A PostgreSQL advisory lock prevents duplicate reconciliation pipelines, and bridge leases prevent duplicate receipt ownership.

The retained cloud helper `/workspace/sentinel-environment/start-integration.sh` starts the existing local PostgreSQL service, securely sources private configuration, applies the head and starts supervision. It is a workspace helper, not a continuously hosted public service. Logs must remain private and must not contain secret values.

## Monitoring and alerts

- `/health`: process only.
- `/ready`: database/schema plus required workers, including stale/future-heartbeat rejection.
- `/operations`: administrator metrics; global inbox aggregates only for the configured installation operator merchant.
- `/monitoring`: origin/time-bounded risk and case metrics; delayed-label and truncated-sample limits remain visible.
- Log categories distinguish proxy CONNECT denial from upstream HTTP authorization. Retain correlation IDs and record IDs, not raw evidence/provider bodies.

A bridge outage keeps events in the remote inbox; never mark them PROCESSED from an attempted HTTP request. Investigate DEAD receipts individually and never rewrite original signed bodies. Normal production forwarding does not claim SIMULATED fixtures.

## Rollback/recovery

Stop the exact managed supervisor, retain the database and evidence, and restore a compatible code revision only after checking schema compatibility. Prefer a forward fix for additive migrations. Never automatically downgrade or reset a live/user database. A manual downgrade removes new workflow tables and is destructive; only run it on a disposable verification database or an explicitly approved restored backup.

A refund left EXECUTING after a crash is ambiguous, not failed. Its balance stays reserved. Use the protected read-only reconciliation path for a known provider refund ID; if no ID is known, require operator/provider investigation instead of automatically resubmitting. Never create a new idempotency key to escape uncertainty.

## Private backups

Use a PostgreSQL custom-format dump stored mode600 outside Git. Evidence/packet bytes live in `stored_blobs` when database storage is configured and therefore join the dump. Restore into a separate disposable database and compare schema, merchant record counts and every blob SHA-256 before claiming recovery. Do not expose the dump or administrator passwords in public artifacts.

A local restored dump is not proof of scheduled hosted backups, offsite retention, encryption policy or point-in-time recovery. Configure and test these on the chosen host before a public release.

## Build-space recovery

The managed VFS Docker builder exhausted the workspace during release verification. Only unused BuildKit caches and untagged unused images were pruned; no database volume, source, private evidence or Git backup was removed. The final Dockerfile assembles its Python runtime in one filesystem layer from read-only source/web mounts to avoid repeated VFS copies of the installed dependency tree. The public CA is supplied as an ephemeral BuildKit secret and TLS verification stays enabled. Current source was rebuilt and its image/source hashes compared.

When capturing build logs, preserve command exit status. After space recovery rerun affected tests/builds from a clean disposable test database. Do not run an intentional supervisor restart at the same time as browser verification that depends on that service.
