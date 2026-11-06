# Final deployment proposal — 6 November 2026

SENTINEL is prepared for a single continuously running Docker service and a separate persistent PostgreSQL database. Deployment remains pending hosting access, a reviewed current quote and validation on the chosen host. No resource was deployed or purchased during this review. No current price, available plan capacity, provider authentication or public Python application URL is claimed.

## Platform choice

| Option | Fit for the existing application | Conditions to verify before purchase |
| --- | --- | --- |
| Render | Existing `deploy/render-continuous.yaml` proposes one Docker web service serving UI and API, plus managed PostgreSQL. API, durable pipeline and inbox bridge share the supervised container. | Current plan availability and price, continuous execution without sleep, memory/CPU under scoring and PDF workloads, database capacity, TLS, backup retention, restoration, proxy addresses and rollout controls. |
| Railway | The same Docker image and a persistent PostgreSQL service are a plausible alternative; no Railway proposal has been applied or tested. | Current minimum/usage charges, always-running behavior, restart/health semantics, persistent DB volume, backup/restore provision, TLS, egress, and ability to stop the old worker before starting another. |
| Vercel frontend | Optional static frontend only. The current production image already serves the built Vite app on the API origin, avoiding an additional service. Vercel does not replace the continuous Python/XGBoost service, PostgreSQL or workers in this design. | A split frontend needs explicit `/api` routing to the backend. Browser code uses relative paths and same-origin credentials, and reads its CSRF cookie on the frontend origin; CORS alone does not make a separate-domain API compatible. Test login, CSRF, uploads, redirects and authenticated downloads through the selected proxy/domain arrangement. Vite's development proxy is not a production deployment configuration. |
| Existing Supabase | Retain the public TypeScript receiver and private inbox. The Python bridge still needs a continuously running host. | Receiver signature verification, service-role isolation, inbox retention/capacity, outbound access and operational backups. Edge execution is not a replacement for this Python worker runtime. |

Verify official current terms at [Render pricing](https://render.com/pricing), [Render Blueprints](https://render.com/docs/blueprint-spec), [Railway pricing](https://docs.railway.com/reference/pricing/plans), [Vercel pricing](https://vercel.com/pricing), and [Supabase pricing](https://supabase.com/pricing). These links are review sources, not evidence of prices verified in this session. Quote compute, PostgreSQL, private storage growth, backups, outbound transfer, logging and taxes together; select limits and alerts before approval. Singapore in the current proposal is a consistent placeholder region, not a measured optimum for the existing inbox.

## Proposal corrections

The Render proposal no longer keeps generated `SENTINEL_SEED_*` passwords in the service environment. `start.sh` runs `app.cli seed` whenever the administrator seed password is present. Previously, `seed` replaced existing account password hashes and retained bootstrap variables silently reset passwords on container restarts. The final release also changes seeding to preserve existing passwords by default; intentional operator rotation requires `--rotate-passwords`. Bootstrap once through a private operator command, supplying passwords securely to that command only. If an initial start must use seed variables, remove them from persistent service settings immediately afterward. Do not put values in source, shell history, logs or public demo instructions. Judge-demo provisioning uses its separate private password flow.

The proposal requests one instance and explicitly requires `SENTINEL_FORWARDED_ALLOW_IPS` through secure operator configuration. Inspect the actual ingress topology and set only trusted proxy addresses/networks; do not guess addresses or use `*`. Existing supervisor validation rejects wildcard trust in hosted mode. Validate forwarded HTTPS and client address behavior on the actual host, including rate limiting.

## Startup and rollout contract

1. Review and publish the exact tested source through an authorized repository/host workflow. Validate the proposal against the hosting provider's current schema before applying it. `autoDeploy: false` avoids unreviewed releases.
2. Back up the application database and verify restoration into an isolated database before migration. Keep it separate from the Supabase inbox. Require the host's supported database TLS configuration and restrict access to the application/operator.
3. Configure hosted production mode, secure cookies, database-backed evidence, worker readiness, and empty same-origin CORS as in the proposal. Supply the paired sandbox PayPal credentials, webhook ID, Supabase URL and private service-role key securely. Leave AI disabled unless an explicit supported model/key and authorized usage budget are configured. No live PayPal mode exists. Refund execution stays disabled unless separately enabled intentionally.
4. Review the migration chain through `d105a4143283`. The proposal and entrypoint pin this target for automatic upgrades; startup then runs `python -m app.cli check-schema` before starting processes. Older deployment documents mentioning `8ab7245e13c0` describe the previous head. For an established database prefer an operator-controlled migration window with `SENTINEL_AUTO_MIGRATE=false` after the reviewed upgrade. Do not run automatic downgrades.
5. Use a controlled replacement with a maintenance window initially. The pipeline owns a database advisory lock and exits when another pipeline holds it. A provider's overlapping/zero-downtime rollout can repeatedly kill the replacement pipeline while the old instance retains the lock. **One desired replica does not prevent overlap during deployments.** Verify the host can stop the previous container first, or redesign/separate worker supervision before adopting that rollout model. The supervisor exhausts its restart budget after five exits. Current readiness checks the shared worker heartbeat table rather than proving that each new container owns its worker, so a green replacement alone does not establish safe handoff.
6. Start API, pipeline and configured bridge under the supervisor. `/api/v1/ready` requires the exact schema and fresh healthy pipeline and bridge when worker readiness is enabled. Both are required by the hosted contract; omitting bridge configuration cannot produce full readiness. Health does not authenticate PayPal or verify a real AI run. Diagnose provider access separately without creating financial actions.
7. On the real HTTPS hostname verify secure cookies, RBAC, CSRF, same-origin downloads, upload limits, denied fixture routes and trusted forwarding. Run isolated authorized fixtures, restart the service and compare downloaded attachment/packet checksums. Verify bridge recovery and worker heartbeats after the restart.

Do not scale the current container horizontally: the pipeline is a singleton and login rate limiting is process-local. Configure shutdown grace to allow supervised children to terminate; draining in-flight HTTP/background investigations needs testing on the chosen host. Interrupted investigation runs may require the existing stale-run recovery and a manual restart rather than resuming automatically.

## Private storage, backups and operations

Use `SENTINEL_STORAGE_BACKEND=database` on ephemeral container filesystems. Evidence and generated packets remain in authenticated application storage rather than a public directory; size PostgreSQL for blob growth, WAL and backups. A persistent database alone is not a backup. Confirm encrypted scheduled backups, retention, recovery point/time objectives, restricted backup access and a successful restore drill. Record coverage separately for the application DB and Supabase inbox/receiver configuration. A local dump or an untested provider plan is insufficient evidence of recovery.

Keep service-role keys and provider keys in host secret settings, never browser build variables. Monitor readiness, unhealthy/stale workers, queue age, bridge failures, disk/database growth and failed investigations. Keep financial operations disabled until their separate verification and authorization are complete. The hosted service remains blocked until credentials/bindings, network access, hosting account/cost approval, rollout controls and backup restoration are verified.

Offline regression checks for the proposal use the existing API review environment (pytest and PyYAML):

```sh
apps/api/.venv/bin/pytest -q deploy/tests/test_render_contract.py
```

These checks catch persistent bootstrap credentials, missing explicit proxy configuration and accidental replica/health contract changes. They do not validate a provider's live Blueprint schema, prove available resources or deploy anything.
