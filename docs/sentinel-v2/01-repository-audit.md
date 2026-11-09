# Repository audit — Phase 1

Baseline: `410109c9304e11d2e1e685600194e290d978c0ab`, verified against GitHub main after the user merged recovered work. The earlier recovered tip `ac044cd` is an ancestor. Main adds static-demo/Pages routing to that implementation; it is not safe to redesign from the old `aed5d56` demo alone.

## Architecture verified in source

- Repository: `harshjha15335/SENTINEL-`. Worktree: `/workspace/SENTINEL-v2`, branch `redesign/sentinel-v2`. Original checkouts were not edited.
- `apps/web`: React/React DOM 19.3.0, TypeScript 5.9.3 strict, Vite 8.3.4, React Router 7.18.4. npm with `package-lock.json`. Versions are package/lockfile facts, not assumed framework defaults.
- Entry: `src/main.tsx`; routes/providers: `src/app/App.tsx`. React StrictMode, React Query 5.104.1, Radix Tooltip and ToastProvider. No separate global state store.
- BrowserRouter uses Vite base; `VITE_ROUTER=hash` selects HashRouter. `VITE_STATIC_DEMO=true` routes API reads through `src/lib/staticApi.ts`, serving a bundled public snapshot and refusing writes. Both modes survive this work.
- Styling: Tailwind 4.3.3 through `@tailwindcss/vite`; `src/styles/tokens.css` defines IBM Plex typography, blue accents and surfaces, global base styles. `grid.css` and AG Grid theme supply table presentation. No Tailwind JS theme config. No existing light/dark theme switch found; baseline is dark.
- Existing primitives are local `src/components/ui`, Radix tooltip, lucide-react 1.55.0. Forms use react-hook-form 7.89.0, Zod 4.6.5. Data grids use AG Grid Community 36.2.0. Charts are native SVG in Policy Lab, Monitoring and Network; no separate chart library is required.
- Existing motion consists chiefly of CSS transitions/loading states. V2 adds GSAP/ScrollTrigger and @gsap/react, plus locally served Fontsource Space Grotesk, Inter and JetBrains Mono. Exact resolved versions are in the lockfile.
- Client API: `src/lib/api.ts`; generated types: `packages/contracts/openapi.ts` from OpenAPI JSON. Same-origin `/api/v1`, cookies, JSON errors, correlation IDs and CSRF headers on mutations. No server credentials belong in Vite variables.
- Auth: `features/auth/session.ts`; `AppShell.tsx`; backend `app/auth/deps.py` and `sessions.py`. `/me` checks the session; shell redirects unauthenticated users. Existing login remembers pathname via router state, not arbitrary query state. Roles ADMIN/ANALYST can operate, VIEWER reads; backend further enforces ownership, tenant scope and independent approvals.
- Backend: FastAPI/SQLAlchemy/Alembic in `apps/api`; entry `app/main.py`; services under `app/services`; PostgreSQL. Webhooks/scoring have durable queues and worker supervision. ML artifacts remain in `ml`/API artifact directories. No backend, contract, migration or model file changed for the preview.
- Build/deploy entrypoints include Dockerfile, compose, Render YAML, manual image and Pages workflows, static exporter. They are inspected as boundaries; no deployment or infrastructure change is needed for Phase 1.

## Local environment and safe testing

Existing installed dependencies and the recovered Python virtualenv were available. V2 has its own copy of web node_modules; installing its five packages did not mutate the old checkout. A dedicated PostgreSQL 16 container `sentinel-v2-db` binds only `127.0.0.1:5544`, database `sentinel_v2_test`. Tests enforce a loopback `_test` database before migrations/truncation. Configured Supabase, payment and AI secrets were not used for UI verification.

After backend tests, the existing CLI seeded this disposable database and loaded 9,051 SYNTHETIC_DEMO payments, 1,811 assessments and 170 review cases. These are local synthetic model outputs, not authentic payment events. The public V2 fixtures are separately authored SIMULATED examples with explicitly illustrative scores.

Frontend baseline before edits: typecheck/lint/build pass; 39 tests pass. Baseline backend: 262 pass, 1 provider-backed skip. ML: 7 pass. See final QA for browser evidence and limitations. No genuine PayPal or paid AI execution was attempted.

## Tests and environment dependencies

- Web unit tests: `src/**/*.test.ts(x)`, Vitest 5.0.3 + jsdom + Testing Library; test utilities match API paths.
- Existing browser tests: `e2e/fixture-flow.spec.ts`, workbench, operations, next-phase, release-read-only and static-demo. Credentials/scenario/build-specific tests have explicit skips; they are not universal green checks.
- API regression tests: auth/CSRF/tenant scope, checkout, risk/cases, evidence, investigations, approvals, refunds/disputes, policy, monitoring, durable jobs, provider construction, hosted/security configuration.
- V2 tests use a separate Playwright config to exercise the development-only routes. Browser binaries beyond system Chromium are unavailable: official Firefox download failed with policy 403; WebKit installation was therefore not completed. This is a verification gap.
- Preview dev server: port 5175; API: local port 8000 in fixture/no-provider mode. Production build preview: port 4175. None is a production deployment.

No repository-owned AGENTS.md existed at discovery. Root AGENTS.md now records the preservation boundary and actual commands; detailed behavior lives in these documents rather than new skills created merely for a count.
