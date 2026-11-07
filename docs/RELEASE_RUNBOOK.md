# Controlled release runbook

This is a reviewable procedure, not deployment or spending authorization. The Render proposal contains deliberately unresolved web/database plan names until an official quote and owner approval exist. Do not apply it as supplied. Select the measured 2 GiB or 4 GiB resource candidate only after validating actual provider plan names, CPU, storage, backups, transfer, logs, region, taxes and costs.

## Before an authorized maintenance window

- Export the Git bundle and checksum independently. Keep the baseline revision and image. Verify private database backup restoration, including evidence hashes, in a separate database.
- Establish actual Render account/source access and explicit cost/publication/deployment authorization. Do not push or attach a private repository automatically.
- Preserve one same-origin Docker UI/API service, singleton pipeline and private database evidence. Supabase is working; do not restore it or re-run remote fixture mutations unnecessarily.
- Configure secure server-side values from deploy/public-release.env.example. Leave refunds false, dispute submission disabled and fixtures unavailable publicly. Use only supported raw/Basic-compatible PayPal delivery. Never copy credentials into command-line arguments, logs or reports.
- Hosted database connections and online Alembic migrations force sslmode=verify-full. The supplied URL cannot downgrade it. System CA roots are the default; a provider/operator CA file may be selected with SENTINEL_DATABASE_SSL_ROOT_CERT. Confirm actual DB hostname/certificate/TLS on the selected host; local tests do not prove that chain.
- Supply actual inspected ingress IPs/CIDRs in SENTINEL_FORWARDED_ALLOW_IPS. Hosted startup rejects missing, malformed, wildcard or collectively unrestricted IPv4/IPv6 scopes before children start. Do not guess the provider networks.
- Keep SENTINEL_AUTO_MIGRATE=false and reviewed target d105a4143283. Review schema compatibility with the rollback image; never automatically downgrade.
- Drain or finish active investigations and scoring work before stopping. An interrupted provider request can have unknown usage; do not automatically resubmit. Retain failed/abandoned audits. Verify the chosen provider supports a real stop-before-start operation: one desired replica and autoDeploy=false do not prevent overlap.

## Authorized replacement sequence

1. Record backup, old image/source SHA, schema revision, current workers and approved configuration. Enter the maintenance window.
2. Stop the exact old supervisor/container using the host's confirmed control. Do not kill unrelated processes or restart Docker/PostgreSQL globally.
3. Confirm the old advisory lock is released. A trusted operator may acquire and immediately release pg_try_advisory_lock(7682346) on the application database using the same short-lived connection. If it cannot be acquired, abort replacement; do not terminate an unidentified backend.
4. Run the API virtualenv/container Alembic command `alembic upgrade d105a4143283` using hosted security/TLS settings. Then run `python -m app.cli check-schema`. These commands must target the application DB, never the Supabase inbox.
5. Start one replacement supervisor. Check its actual child processes and lock ownership, not only shared historic heartbeat rows.
6. Verify fresh pipeline and Supabase successful-poll timestamps. Required `/api/v1/ready` must return 200 honestly. `/api/v1/health` alone is insufficient.
7. Verify public HTTPS, forwarded scheme/client identity, secure cookies, CSRF, login/logout, session persistence, judge write denial, cross-merchant denial and private evidence/packet checksums.
8. Verify database persistence and hosted backup/isolated restore, retention and access restrictions. A local dump is not proof of managed backups/PITR.
9. Run authorized isolated staging fixtures only. Do not enable a public production fixture route or use a simulator to claim genuine PayPal delivery.
10. Record public URL, image/source SHA, effective environment revision, tests, worker ownership, metrics and screenshots. Leave auto-deploy off.

## Rollback

Stop the exact replacement safely, preserve its data/audits, and restore a compatible reviewed image only after verifying schema compatibility. Prefer a forward fix for additive changes. No automatic downgrade, data overwrite or live restore is authorized by this runbook.

## AI verification boundary

The production factory retains Chat Completions. Responses was compared offline; neither proves the requested model/account supports it. SDK retries default to zero. Output and local per-request/cumulative input byte limits are enforced; logical request/tool/usage budgets and timeout remain active. These are not exact dollar caps. Missing provider usage is unknown, not free. Review current model prices, account controls and retry settings, then obtain explicit approval for one bounded synthetic-case investigation. No actual inference follows merely from having a key.
