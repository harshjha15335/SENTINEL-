# SENTINEL V2 — Phase 1 handoff

Verdict: PROTOTYPE READY FOR DESIGN APPROVAL (subject to the recorded QA limitations).

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

Neither readiness nor the user's merge of main constitutes design, route migration or deployment approval. Gate 1 authorizes beginning Prompt 2; no full migration has begun.

## Identity and restoration

- Repository: `https://github.com/harshjha15335/SENTINEL-`.
- Actual worktree: `/workspace/SENTINEL-v2` (separate from existing `/workspace/SENTINEL-` and `/workspace/SENTINEL-recovered`).
- Working branch: `redesign/sentinel-v2`.
- Authoritative baseline: `410109c9304e11d2e1e685600194e290d978c0ab`, verified by fetching GitHub main after user confirmation.
- Earlier discovery baseline: `ac044cd3b114ff82b8e5ff4ef3e650e541973499`; verified ancestor of main. Isolated initial prototype files were retained during fast-forward to approved main.
- Original selected worktree was clean before our changes; no unrelated dirty files were incorporated.
- Baseline ref: `backup/sentinel-v2-main-410109c`.
- Prototype SHA: `2a1705e9712770c16e2e2b1b81d658d42d258dea`.
- Current working-tree status: Phase 1 source is locally committed; verify with `git status --short --branch` in any subsequent session.
- Baseline recovery bundle: `/workspace/sentinel-v2-artifacts/baseline/main-410109c.bundle`; `git bundle verify` succeeded, full history included.

Safe recovery without discarding the prototype: `git worktree add /workspace/SENTINEL-v2-baseline backup/sentinel-v2-main-410109c`. For another machine, clone the verified baseline bundle into a new directory. Do not reset/clean/overwrite an existing working tree. Prototype source is separately checkpointed on the redesign branch; an additional final bundle is retained outside the repository.

## What is implemented

1. Evidence Reel: original SVG machine with linked spools/tape/scanner, six deterministic reversible stages, chapter controls, skip-story focus, reload restoration and breakpoint cleanup.
2. Demo Payment Dossier: two labeled authored fixtures, selectable examples, overview/timeline, provenance, illustrative factors and scores, responsive app-shell composition.
3. Authorized records preview: existing session and API hooks; list/search, id deep link, typed dossier, recorded assessment/limitations and links to existing cases. Read-only; original mutations remain in untouched existing screens.
4. Production isolation: DEV-only lazy import and scoped styles/cache; normal and static/hash production builds emit no preview assets. No new preview polling or providers mount on normal routes.
5. Repository/feature/action/state/route audit, browser tests, baseline restoration bundle and QA evidence.

No existing page, domain hook, API client, backend file, model, migration, contract, deployment workflow or legacy styling file was removed or rewritten.

## Preview instructions

From `apps/web`: `npm ci`, then `npm run dev -- --host 0.0.0.0 --port 5175`.

- Reel: `http://localhost:5175/__v2-preview`.
- Demo dossier: `http://localhost:5175/__v2-preview/dossier`.
- Authorized records: `http://localhost:5175/__v2-preview/workspace` (existing local API/session required; no fixture fallback).

URLs refer to the execution environment, not an externally deployed site. No tunnel or public preview was published. Demo reel/dossier need no backend credentials. The app's existing API proxy defaults to local port 8000.

For this cloud session only, a disposable PostgreSQL container `sentinel-v2-db` uses loopback port 5544; database `sentinel_v2_test`. API is local port 8000, PayPal fixture mode, AI provider none, provider credentials removed from the API subprocess. Private local seed credentials live outside the repository at `/workspace/sentinel-v2-private/local.env`, permissions 0600. Never publish this file or capture filled password fields. The database and runtime are not part of the source handoff.

## Verification commands

From `apps/web`:

```sh
npm run typecheck
npm run lint
npm test
npm run build
VITE_STATIC_DEMO=true VITE_ROUTER=hash npm run build -- --outDir /workspace/sentinel-v2-artifacts/static-build
SENTINEL_SCREENSHOT_DIR=/workspace/sentinel-v2-artifacts SENTINEL_V2_TEST_CREDENTIALS=/workspace/sentinel-v2-private/local.env npx playwright test --config playwright.v2.config.ts
SENTINEL_V2_ARTIFACTS=/workspace/sentinel-v2-artifacts node scripts/measure-v2.mjs
SENTINEL_V2_ARTIFACTS=/workspace/sentinel-v2-artifacts SENTINEL_V2_STATIC_DIST=/workspace/sentinel-v2-artifacts/static-build node scripts/check-v2-production.mjs
```

Production isolation script expects `npm run preview -- --host 127.0.0.1 --port 4175` and the two completed production builds. Paths above describe this execution; scripts/tests default to local test-results artifact directories and accept environment overrides. A new machine must supply its own disposable test environment and browser installation.

Backend: from `apps/api`, with an explicitly dedicated loopback `_test` database, run `.venv/bin/pytest -q` in fixture/no-provider mode. This session used `/workspace/SENTINEL-recovered/apps/api/.venv/bin/pytest` to avoid reinstalling an already available environment. ML from root: `PYTHONPATH=apps/api:ml <python-env>/bin/pytest ml/tests -q`.

Do not run destructive backend tests against the seeded preview database while demonstrating the UI. Its test conftest truncates/migrates disposable tables. After backend tests we seeded the preview using existing CLI commands, not database/schema changes to any operational environment.

## Review artifacts

All captures are outside public assets/source: `/workspace/sentinel-v2-artifacts/`.

- `reel-0.png` through `reel-5.png`: idle through final reveal.
- `reel-mobile.png`, `dossier-desktop.png`, `dossier-mobile.png`.
- `dossier-authorized.png`: actual local synthetic API output.
- `reel-demo.webm`: forward/backward browser recording of the public-safe scene.
- `baseline/`: original screenshots, comparison screenshots, baseline bundle and regression logs.
- `final-browser.log`, `legacy-browser.log`, `performance.json`, `performance-initial.json`, `production-isolation.json`, production build logs, browser-install failure log.

A subsequent session must verify source SHA and artifact availability rather than assume filesystem persistence. Screenshots can be regenerated with the documented commands. Do not publish baseline audit captures, credentials or authentication-bearing traces.

## Gate 1 decisions still required

- Evidence Reel design/material treatment: PENDING.
- Operational shell/dossier composition: PENDING.
- Representative workflow: transaction context/risk/associated case, implemented; user approval PENDING.
- Visual adjustments: none approved yet.
- Public `/` vs protected `/app` migration and compatibility aliases: PENDING, see route plan.
- Full legacy UI migration: NOT AUTHORIZED until explicit Gate 1 approval.

Known limits: cross-browser downloads blocked, no physical-device or manual screen-reader check, genuine providers unverified, startup timing varies and production/field performance is not established, prototype reveal still needs Phase 2 polish. These do not authorize deletion of unverified existing screens. The final full-rebuild/deployment verdict remains NOT READY — BLOCKERS REMAIN.
