# Route plan — NOT APPROVED FOR CUTOVER

Phase 1 changes no existing route identity. `App.tsx` adds one DEV-only lazy route outside AppShell: `/__v2-preview/*`. Production eliminates its import and assets; existing wildcard behavior handles that path. Marketing demo pages use no session/data requests; `/__v2-preview/workspace` requires the existing `/me` check and server authorization for every read.

| Existing | Purpose | Proposed Phase 2 alias/canonical destination | Status |
|---|---|---|---|
| `/` | Protected Command Center | `/app`; `/` becomes public marketing | User approval pending |
| `/transactions` | Filters, pagination, grid | `/app/transactions` | Preserve old alias and q/status/origin/page |
| `/transactions/:id` | Details, risk, associated cases | `/app/transactions/:id` | Preserve id and deep link |
| `/cases`, `/cases/:id` | Queue, investigation workbench | `/app/investigations`, `/app/investigations/:id` | Preserve filters, id and refund/dispute links |
| `/model` | Model card/metrics | `/app/risk` | Preserve old alias |
| `/policy` | Validation simulation and shadow proposals | `/app/policy-lab` | Preserve old alias; no activation |
| `/monitoring` | Risk monitoring | `/app/monitoring` | Preserve filters supported by source |
| `/network` | Relationship explorer | `/app/network` | Must not be omitted from navigation |
| `/operations` | Admin webhook/worker operations | `/app/operations` | Admin check unchanged |
| `/refunds`, `/disputes` | Financial review/preparation | `/app/refunds`, `/app/disputes` | Preserve `case` query and restrictions |
| `/checkout` | Sandbox/fixture checkout | `/app/checkout` | No payment executions during redesign tests except explicitly local fixture tests |
| `/demo` | Private prepared judge scenario | `/app/demo` | Preserve DEMO merchant/viewer behavior |
| `/settings` | Connection diagnostics and admin audit | `/app/settings` | Integrations remain here unless separately approved |
| `/login` | Existing auth form | Keep `/login` | Preserve roles, cookies, expiry, logout |
| wildcard | Protected not-found page | Appropriate public/protected not-found | Must not leak private data |

Proposed `/app` structure is a recommendation, not a route change. A dedicated `/app/integrations` page does not currently exist and must not be invented to fill navigation.

## Root decision requiring Gate 1

Currently `/` checks the session, redirects unauthenticated visitors to `/login`, and shows Command Center after login. Proposed: all visitors can see the marketing homepage; operational entry is `/app`, protected by the existing session. Post-login default would become `/app`; explicitly requested safe local deep links should win. Logout would return to the approved public or login destination. These changes require explicit user approval and tests before cutover.

The old root bookmark cannot simultaneously remain a dashboard and become public marketing. The handoff must record acceptance of that behavior change. All non-root old routes should retain an intentional alias/redirect with required query parameters. Avoid redirect loops and preserve browser history deliberately, using replace for compatibility redirects.

## Preview specifics

- Reel: `/__v2-preview`.
- Public-safe dossier: `/__v2-preview/dossier?example=0|1`; invalid values select the first deterministic example. Selection survives refresh/history.
- Authorized list/dossier: `/__v2-preview/workspace?q=...&id=...`. q uses the existing order/capture search; it does not invent UUID search. Synthetic records may legitimately have null provider IDs, so `id` deep links remain supported.
- Existing login can receive the preview return path including query through router state. Normal application authentication behavior remains unchanged.
- Production, Pages and hash builds exclude the V2 import via `import.meta.env.DEV`. No preview deployment is configured or authorized.
