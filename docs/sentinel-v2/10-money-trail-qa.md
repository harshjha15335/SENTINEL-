# Follow the Money — executed QA and review handoff

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

This is an isolated visual prototype checkpoint, not Gate 1 approval or a full migration.

## Executed checks

- Frontend: 43 passed across 14 files, including the preserved 39 operational tests and four replacement money-journey tests. Final run used `npm test -- --maxWorkers=1`. An unchanged Disputes test timed out during an earlier contended parallel run; the complete suite passed when rerun. No legacy test was weakened.
- Backend: 262 passed, one skipped, exit 0. `/workspace/SENTINEL-recovered/apps/api/.venv/bin/pytest -q` from `apps/api`, with `SENTINEL_DATABASE_URL` pointing to the separate loopback `sentinel_visual_revision_test` database. Fixture/no-provider tests; no operational database used. Double-quiet pytest configuration suppresses the standard summary; counted progress markers are recorded in the log.
- Chromium: 19 passed in the complete final money/companion-receipt suite. It verifies actual session → API → PostgreSQL transaction/risk → dossier → existing case, genuine error/expiry/empty states, filter queries/pagination/current-page sort, seven story stages, forward/reverse, refresh/history, correct entry scroll, breakpoint cleanup, mobile/reduced motion, keyboard skip and accessibility.
- After removing simultaneous headline crossfades, three affected scroll/transition cases passed again, including a single-visible-headline assertion and selected coral / companion purple assertions. Chapter links land after the fade-in interval.
- Additional axe WCAG 2/2.1/2.2 AA desktop/mobile audits: Command Center and dossier, zero violations. Early contrast defects in the critical pill and queue numbers were corrected.
- TypeScript, lint, normal build and static/hash build: passed. Production preview isolation verifies no preview root, requests or assets, including the new fonts and visual components.
- `git diff --check`: passed. Backend, models, API contracts, auth, infrastructure and legacy-screen source diffs: empty.

Logs are outside source at `/workspace/sentinel-money-trail/evidence/`; selected share-safe logs are in the approval ZIP. Authentication-bearing Playwright traces, private env files and raw duplicate recordings are excluded.

## Browser capture review

24 new screenshots: seven 1440×900 desktop story compositions at 1× and 2×, full desktop dossier and Command Center at both densities, and viewport/full-page captures of mobile homepage, dossier and Command Center at 390×844 CSS pixels / 2×. Equivalent original and proposed API payment captures use the same local synthetic transaction; origin labels remain visible. Original vs proposed Command Center comparison explicitly distinguishes real local synthetic API data from the new authored composition prototype.

Two native browser recordings use `mouse.wheel` input: full forward/reverse scroll, and final receipt/shared-layout expansion followed by actual CTA entry. MP4 encoding preserves timing. Videos may include the initial development preview loading frame; no prerecorded animation is substituted for scrolling. Final CTA entry opens at the top with the workspace heading visible.

Rendered captures and sampled video frames were inspected, not only animation attributes. Wallet depth, pocket occlusion, main/companion receipts, coral isolation, connected signals, casefile expansion and entry were inspected. The original cassette/strip artwork and the rejected graphite/lime identity are absent from the replacement preview.

## Material review limits

Wallet rendering is original layered SVG, not photorealistic realtime 3D. The shared live dossier expands from the selected receipt bounds; intermediate typography scales non-uniformly and resolves at the full layout. This is not a per-field morph. Mobile intentionally uses a readable vertical narrative and opening wallet rather than the desktop flying-object/pinned scene.

No Firefox/WebKit, physical-device, manual screen-reader or genuine external-provider validation. Headless development frame timing is diagnostic only; raw performance measurements are delivered separately. Do not claim sustained 60 FPS, field INP or production readiness. Existing production chunk-size warnings remain visible in build logs.

## Review and recovery

Read `09-money-trail-reset.md` for the implementation contract, palette, fonts and scope. Extract `/workspace/shared/downloads/SENTINEL-Follow-the-Money-approval.zip` and open `index.html` for offline comparison and playback. `REPORT.txt` contains exact current Git SHA, limits and recovery commands. Verified pre-reset bundle: `/workspace/sentinel-money-trail/before-money-trail.bundle`. Final bundle: `/workspace/sentinel-money-trail/money-trail-checkpoint.bundle`.

No push, merge, deployment, route cutover, legacy removal or broad Phase 2 migration occurred. The next decision is visual approval of this replacement direction.
