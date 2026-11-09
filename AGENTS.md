# SENTINEL

- Preserve backend, trained ML artifacts, API contracts, merchant isolation, CSRF, and server role checks.
- V2 is a complete visual replacement implemented incrementally. During Phase 1 keep all existing screens intact. Do not restore retired presentation after migration.
- Read `docs/sentinel-v2/00-handoff.md` and the feature/workflow matrix before V2 changes. Design and route approval are pending until explicitly authorized by the user.
- Preview styling, providers and side effects must remain isolated. The preview must not exist in production builds.
- Distinguish SIMULATED, SYNTHETIC_DEMO, MERCHANT_PROVIDED and LIVE_SANDBOX data. Never fabricate model outputs, provider events, healthy statuses or successful checks.
- No real payments, paid inference, secrets in bundles/screenshots, production mutations, pushes, merges or deployment without explicit authorization.
- Preserve valid existing test coverage. Verify significant UI changes in a browser, including keyboard, mobile, reduced motion, errors and API behavior.
- Web commands from `apps/web`: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`; prototype tests: `npx playwright test --config playwright.v2.config.ts`.
- Backend commands from `apps/api`: `.venv/bin/pytest`, `.venv/bin/ruff check app tests alembic`, `.venv/bin/mypy app`. Destructive tests require a dedicated loopback database ending in `_test`. Never use a user's operational database.
- Follow relevant project context in `CLAUDE.md`; old visual token guidance applies to existing screens only, not the isolated V2 design.
