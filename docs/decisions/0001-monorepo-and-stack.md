# 0001 · Monorepo with one API service and one SPA

Status: accepted (2026-10-10)

**Context.** One month to a hackathon deadline; the judged product needs a PayPal-integrated
backend, an ML pipeline and a polished UI. The brief warns against architecture for appearance.

**Decision.** One repository: `apps/api` (FastAPI, single deployable), `apps/web` (Vite React SPA),
`ml/` (offline training, Phase 3), `packages/contracts` (OpenAPI JSON + generated TS types).
PostgreSQL is the only stateful service. No microservices, queues or graph DB.

**Consequences.** Simple local setup and deployment (one API, one static site, one database).
API contract drift is caught because the web types are generated from the API schema
(`scripts/gen-contracts.sh`) and type-checked in CI.
