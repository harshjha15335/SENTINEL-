# Phase 1 QA and approval package

Prototype verdict: PROTOTYPE READY FOR DESIGN APPROVAL.

Full V2/deployment verdict: NOT READY — BLOCKERS REMAIN. This is a design/integration prototype; the old product remains intact.

## Story verified

A visitor operates an original Evidence Reel using scroll and can open the deterministic public-safe dossier. An authorized merchant can use the existing session → existing API → local PostgreSQL data → typed dossier → associated existing case. Provider execution is not part of that claim.

## Results

| Check | Actual result | Scope / evidence |
|---|---|---|
| Frontend typing | PASS | npm run typecheck |
| Frontend lint | PASS | npm run lint |
| Existing unit tests | 39 PASS / 13 files | npm test; no existing test deleted |
| Normal production build | PASS | npm run build; existing AG Grid chunk-size warning remains |
| Static/hash production build | PASS | VITE_STATIC_DEMO=true VITE_ROUTER=hash; no preview emitted |
| Backend regression | 262 PASS, 1 SKIP | Dedicated loopback PostgreSQL 16 database; real-provider integration skipped |
| ML tests | 7 PASS | Existing models/artifacts unchanged |
| V2 Chromium browser suite | 14 PASS | Final browser log; includes two actual local API integration flows |
| Existing selected browser flows | 10 PASS, 2 SKIP | Desktop/mobile fixture checkout, reviews, auth boundary, admin operations, evidence/packet/independent approval; prepared judge scenario absent |
| Production exclusion smoke check | PASS | No preview root, no preview requests/assets in normal or static output; existing login behavior retained |
| Desktop visual preservation | Exact PNG match | Baseline vs V2 existing Command Center at 1440×900 |
| Mobile visual preservation | 37 edge pixels differ | Same 687×1546 full-document render from 390×844 viewport; differences limited to right rounded-border edge x685–686; no visible layout change |
| Secret value/source/bundle check | PASS: zero matches | Known configured/seed credential values did not occur in changed source or emitted JS/CSS; bounded check, not a comprehensive security audit |
| Firefox/WebKit | BLOCKED | Official Firefox installation returned policy 403 on download hosts; WebKit not installed; not counted as a pass |
| Physical device and manual screen reader | NOT TESTED | Viewport emulation and axe do not establish these |
| Genuine PayPal / paid AI | NOT TESTED | Zero provider-backed UI test operations; fixture and scripted tests are not genuine events |

Existing browser flows mutate only the disposable local fixture environment: simulated capture, case/evidence/packet creation and independent intent approval. No genuine payment/refund, external dispute submission, paid inference, operational Supabase mutation or infrastructure mutation occurred.

## Functional and visual findings

- Mid-scroll refresh initially lost progress because lazy scene mounting left the document too short for native restoration. Fixed by saving normalized progress on pagehide and restoring after scene/font setup; reverse/refresh test now passes.
- Heading currency spacing corrected for accessible names. Mobile operational text increased, facts stack at narrow widths, essential controls remain reachable.
- Scroll updates use cached references and GSAP quick setters rather than creating repeated set operations and querying all scene elements every frame. React state does not update per scroll tick.
- Any preview API 401 clears its private cache and returns to a sign-in gate. Errors/empty data stay errors/empty data; they never become public demo content.
- Synthetic seed records correctly have null PayPal order IDs. Deep links are tested; no fake order IDs were added to actual API records.
- Desktop and mobile idle/dossier/screens, six story checkpoints, authorized dossier, reduced motion, errors and selected original flows were reviewed through actual browsers. Static marketing numbers are visibly illustrative; authorized values come from the API.
- Mobile baseline comparison exposed an existing full-document overflow/width issue in the old dashboard under desktop-context viewport emulation. It occurs in both baselines; do not claim Phase 1 fixed the old layout. Phase 2 must rebuild it intentionally. Existing configured mobile-device browser tests passed their own overflow assertions.

## Accessibility

Axe WCAG 2/2.1/2.2 A/AA scans passed on the tested reel, demo dossier, mobile dossier, reduced-motion story, unauthenticated preview and authorized dossier. Existing selected browser tests also run their own axe checks. Keyboard skip moves focus beyond the pin; native chapter/example/view/search controls have accessible names; inactive animated stages are inert. No full WCAG conformance certification is claimed. Browser emulation is not physical-device validation.

## Performance — lab only

Environment: headless system Chromium 154.0.8037.57, 1440×900, localhost Vite development server, no CPU/network throttle, shared cloud executor. Three fresh browser contexts. This is deliberately a development-only route; optimized public production performance cannot yet be established.

After reducing scroll work:

| Run | LCP ms | CLS | Median / p95 frame interval ms | Frames >50ms | Scroll long tasks >=50ms |
|---|---|---|---|---|---|
| 1 | 1712 | 0.000080 | 16.7 / 16.7 | 0 | 0 |
| 2 | 1752 | 0.000080 | 16.7 / 16.8 | 0 | 0 |
| 3 | 2512 | 0.000080 | 16.7 / 33.4 | 2 | 0 |

Initial measurements under concurrent browser activity showed LCP 2608–3752ms and p95 frame intervals up to 83.3ms. Code and executor contention both changed between runs, so the improvement is not a controlled attribution solely to optimization. Retain performance-initial.json and performance.json. No sustained 60 FPS or field p75 claim; no real-user INP data. LCP<=2.5s, CLS<=.1 and INP<=200ms remain objectives; run 3 narrowly misses the LCP objective. Cold module/font evaluation still produces initial long tasks. Further production profiling belongs to Phase 2.

## Review artifacts and limitations

See 00-handoff for paths/commands. Sources and checkpoints are in Git; screenshots/videos/bundles are internal local review artifacts outside public assets. Phase 2 still needs full application migration, the final product-workspace transformation, remaining marketing sections, cross-browser checks and final security/accessibility/performance review. Gate 1 design/route approval and Gate 2 deployment approval are both PENDING. No push, remote merge, publication or deployment was performed by this implementation task.
