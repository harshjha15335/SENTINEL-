# Current Gate 2C loading stability

See [17-gate2c-loading-stability.md](17-gate2c-loading-stability.md). Targeted frontend loading geometry and font timing only; design remains APPROVED and deployment remains PENDING. No host publication is authorized.

# Current Gate 2B host preparation

See [16-gate2b-host-preparation.md](16-gate2b-host-preparation.md). Cloudflare Pages configuration is isolated from the approved portable application. Preparation and local validation only; deployment remains PENDING.

# Current Gate 2A static corrections

See [15-gate2a-static-remediation.md](15-gate2a-static-remediation.md) for snapshot consistency, build gates and static capability boundaries. Design remains APPROVED; deployment remains PENDING. The private review Site is unchanged.

# Current private preview correction

See [14-private-preview-overlap.md](14-private-preview-overlap.md). The owner-private read-only Site is authorized for review; operational deployment remains PENDING. The dossier-entry overlap correction moves its CTA below the pinned reveal. Historical publication restrictions below refer to the earlier delivery and the operational app.

# Current reconstruction — Phase 2

See [13-phase2-reconstruction.md](13-phase2-reconstruction.md) for production routes, functionality preservation, verification and legacy removal. Gate 1 is APPROVED. Deployment/Gate 2 is PENDING. Older sections below are historical.

# Current authority — Gate 1 APPROVED, Phase 2 authorized

Read [12-phase2-authorization.md](12-phase2-authorization.md). User approval on 10 November 2026 supersedes historical design-PENDING markers below. DESIGN APPROVAL: APPROVED. DEPLOYMENT APPROVAL: PENDING. Complete frontend reconstruction is authorized; publication is not.

# Current checkpoint — final Gate 1 visual polish

Read [11-gate1-polish.md](11-gate1-polish.md) first. It supersedes the miniature/scaled workspace reveal in the earlier Follow the Money prototype. The preferred direction is accepted subject to review; DESIGN APPROVAL and DEPLOYMENT APPROVAL remain PENDING. Phase 2 has not begun.

# Current direction — Follow the Money

The user rejected the reel and graphite/lime identity. Read [09-money-trail-reset.md](09-money-trail-reset.md) and [10-money-trail-qa.md](10-money-trail-qa.md) for the executed verification and review limits. Document 09 covers the replacement wallet narrative, ivory/purple identity, horizontal navigation, casefile layout and explicit prototype scope. Earlier descriptions below are historical and superseded for visual direction.

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

# SENTINEL V2 — Phase 1 handoff

Verdict: VISUAL CORRECTIONS READY FOR REVIEW. The technical foundation was accepted, but the original visual design was not approved. See 08-visual-corrections-review.md for the current correction pass.

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
- Prototype SHA: `4f1954f9cb1d5d8ac53c896b5fdcd5a85be65234`.
- Current working-tree status: Phase 1 source is locally committed; verify with `git status --short --branch` in any subsequent session.
- Baseline recovery bundle: `/workspace/sentinel-v2-artifacts/baseline/main-410109c.bundle`; `git bundle verify` succeeded, full history included.

Safe recovery without discarding the prototype: `git worktree add /workspace/SENTINEL-v2-baseline backup/sentinel-v2-main-410109c`. For another machine, clone the verified baseline bundle into a new directory. Do not reset/clean/overwrite an existing working tree. Prototype source is separately checkpointed on the redesign branch; an additional final bundle is retained outside the repository.

## What is implemented

1. Evidence Reel: original SVG machine with changing wound packs, linked tape/scanner, a continuous outgoing evidence strip, attached signal frames, spatial recession and shared React dossier reveal. Six deterministic reversible stages, chapter controls, skip-story focus, reload restoration and breakpoint cleanup remain.
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
- Visual foundations: the user requested retaining graphite/ivory, Volt Lime and typography. The original stationary storytelling was rejected; the targeted correction is implemented. Overall design approval remains PENDING.
- Public `/` vs protected `/app` migration and compatibility aliases: PENDING, see route plan.
- Full legacy UI migration: NOT AUTHORIZED until explicit Gate 1 approval.

Known limits: cross-browser downloads blocked, no physical-device or manual screen-reader check, genuine providers unverified, and production/field performance is not established. Local software-rendered motion still has frame-timing limits; the scene remains a stylized SVG interpretation. The real shared-layout reveal is now implemented, but its artistic acceptance is pending. These do not authorize deletion of unverified existing screens. The final full-rebuild/deployment verdict remains NOT READY — BLOCKERS REMAIN.

## Visual correction pass

- Exact pre-correction checkpoint: `53c42953cd9fb99ed0af4ced3238e2c6317873b9`.
- Recovery ref: `backup/sentinel-v2-before-visual-corrections`; verified bundle at `/workspace/sentinel-v2-revision/before-corrections.bundle`.
- Current prototype/source checkpoint: `4f1954f9cb1d5d8ac53c896b5fdcd5a85be65234`.
- The provided 90-second Wispr Flow-labeled reference clip was downloaded and visually studied. The earlier transfer blocker is resolved.
- New recordings/screenshots/gallery: `/workspace/sentinel-v2-visual-corrections/`.
- Updated shareable ZIP: `/workspace/shared/downloads/SENTINEL-V2-visual-corrections.zip`.
- Current verification logs: `/workspace/sentinel-v2-revision/artifacts/`.
- Read `08-visual-corrections-review.md` and the revised animation contract before continuing. Do not infer Gate 1 approval from this correction request or these test results.

DESIGN APPROVAL: PENDING
DEPLOYMENT APPROVAL: PENDING
