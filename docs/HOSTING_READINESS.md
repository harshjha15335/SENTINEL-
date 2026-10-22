# Continuous hosting readiness — 22 October 2026

The public Supabase receiver is deployed. The Python API, frontend, pipeline and inbox bridge currently run under supervision inside a temporary workspace. There is no verified public Python application URL.

## Prepared architecture

Use one continuously running non-root Docker service plus a persistent PostgreSQL database, retaining the existing Supabase private inbox. FastAPI serves the built frontend and API from one origin. Database-backed evidence keeps attachments and packets out of ephemeral container storage. The supervisor starts API, reconciliation/scoring pipeline and configured bridge. Host readiness is `/api/v1/ready`; it checks the exact Alembic head and, when required, fresh essential workers. Docker health now uses readiness as well.

`deploy/render-continuous.yaml` is a **review-only, paid** proposal: starter Docker service and basic-256mb PostgreSQL, both Singapore, auto-deploy disabled. The application database is separate from the Supabase inbox. Singapore is a prepared consistent region, not a measured latency optimum for the Tokyo inbox. Neither plan's current price, memory headroom under sustained load, account eligibility nor availability has been verified. Benchmark real workloads before committing to a plan.

## Provider comparison and evidence limits

Official documentation was requested on 22 October 2026. Workspace egress returned HTTP CONNECT 403 for the following documentation hosts; these were proxy denials, not provider pricing responses. No hosting credential names or usable hosting connectors are available here. Existing authenticated Supabase project access is available.

| Option | Suitability and limits | Official source to verify before approval |
|---|---|---|
| Render | Prepared single-container/managed-Postgres proposal. The old free demo blueprint is not a continuous-worker guarantee. Verify sleep, memory, DB retention, backups, restart policy and current plans. | https://render.com/pricing and https://render.com/docs/free |
| Railway | Could run the same Docker service and PostgreSQL. No connected account inspected. Verify minimum charges, metering, volumes, health checks and persistent worker behavior. | https://docs.railway.com/reference/pricing/plans |
| Existing Supabase | Reuse the hosted TypeScript receiver and private inbox. It does not deploy this Python/XGBoost service. An edge function's execution limits are unsuitable as an assumption of perpetual Python worker hosting. | https://supabase.com/pricing and https://supabase.com/docs/guides/functions/limits |
| Codespaces / current workspace | Useful development/demo runtime, with stop/rebuild/session/quota constraints. It has not been established as an unattended, continuously available production host. | https://docs.github.com/en/billing/concepts/product-billing/github-codespaces |

**Cost approval is pending.** No current dollar estimate is represented as verified. Obtain an official quote for compute + PostgreSQL + storage + backups + outbound usage + taxes, with billing interval and region. Do not apply the proposal, upgrade an account or accept recurring charges until the user approves that quote. No resources were purchased. Existing connected Supabase resources are reused without plan upgrades.

## Deployment procedure once prerequisites are met

1. Independently download and verify the Git bundle, then authorize publication of the tested branch or provide a host capable of building the preserved source. Public main lacks this implementation. Recovered checkout `origin` is the other local clone; it is not GitHub.
2. Confirm provider pricing, plan resources, continuous worker support, health/restart semantics, account access and cost approval. Validate the blueprint against the provider's current schema before applying it.
3. Provision the independent application PostgreSQL database with TLS as required by that host. Never apply the application Alembic chain to the Supabase public inbox schema.
4. Securely supply the variables documented in WEBHOOK_OPERATIONS.md. Set `SENTINEL_HOSTED_DEPLOYMENT=true`, production, secure cookies, database storage, worker-required readiness, and empty same-origin CORS or explicit HTTPS origins. Hosted configuration rejects insecure combinations. Configure the actual trusted proxy addresses; wildcard trust is rejected. The default is loopback only and must not be claimed to recognize an uninspected provider proxy.
5. Review migrations first. Container automatic migration targets the explicitly reviewed revision `8ab7245e13c0`, not an arbitrary future head. Set `SENTINEL_AUTO_MIGRATE=false` for operator-managed migrations; `python -m app.cli check-schema` then rejects mismatched code/schema before workers start. Only additive nullable fields are added by the Session 8 migration. Downgrades are manual and destructive; run them only against disposable databases.
6. Start one instance initially. The login limiter remains process-local; do not scale horizontally before providing a shared limiter. The pipeline advisory lock rejects a competing pipeline; bridge leases remain safe across instances.
7. Verify HTTPS, secure session cookies, forwarding/header behavior, CORS, readiness, UI, session/RBAC/CSRF, worker heartbeats and fixture-route rejection on the actual hostname.
8. Run isolated integration fixtures, restart the service, download evidence and packets, compare checksums and verify backup restoration into a disposable database.
9. Configure and test scheduled encrypted backups, retention, alerting and restoration. A local dump alone is not a managed backup or disaster recovery guarantee.
10. Provision the isolated judge demo with a private viewer password. Deliver credentials privately; never publish administrator passwords or make merchant workspaces publicly writable.

## Reproducibility and limitations

Direct application dependencies are pinned and the web lockfile is used. Base image tags and Python transitive/build dependencies are not fully digest/lock pinned; byte-for-byte reproducibility is not claimed. Optional BuildKit `build_ca` supplies trusted CA roots without disabling TLS. Inspect image/package vulnerabilities as part of the selected host's release process; a vulnerability scan has not been represented as passed.

The workspace's retained helper and private configuration are tested in this instance. Publication/restoration of a fresh cloud task has not been verified. The service will not continue processing solely because the Edge receiver remains public.
