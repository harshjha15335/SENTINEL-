# Render internal TLS — owner approval required

`render-internal-tls.patch` is inert review material, **not applied code**. It includes
proposed configuration, connection-policy and Blueprint changes. Neither active
Blueprint enables the exception. Active hosted SQLAlchemy/Alembic/worker policy
remains `verify-full`.

The proposal uses `sslmode=require` for a single owner-reviewed Render internal
host, database and user, only in the hosted staging/fixture/no-AI scope. It provides
encryption without server-certificate authentication. This is a material security
trade-off: a private hostname or a configuration flag alone is not cryptographic
proof of the server's identity.

The owner must approve that exact trade-off and authenticate the actual database,
workspace, project and region through Render. No actual host has been provisioned
or approved. The guard rejects external/IP/unreviewed hosts, wrong ports, query
connection overrides, sandbox/AI/refund modes, explicit CA overrides and non-staging
use. Production continues to use strict certificate and hostname verification.

Syntax, patch applicability and an isolated offline guard probe pass: one scoped
fake host permitted and 12 invalid scopes rejected. This is not hosted TLS proof,
and the proposed patch is not part of the active-runtime full regression baseline.
Applying it needs explicit owner approval, dedicated regressions, full acceptance
and a new reviewed commit. It does not authorize Blueprint creation or deployment.

Use a database-first manual sync only after spending/provisioning approval, with
`deploy/render-staging-database.yaml`. Verify its actual internal host through the
owner's authenticated Render account. A later manual update of the SAME Blueprint
to the reviewed application manifest can securely supply that exact host input.
Review both plans separately; do not create duplicate Blueprints or adopt unrelated
resources. Auto Sync must remain false throughout.

If strict certificate authentication is mandatory, do not apply this patch. Use a
reviewed external endpoint with verified CA/hostname and bounded egress allowlist.
That alternative needs actual endpoint/network evidence and revised configuration.
