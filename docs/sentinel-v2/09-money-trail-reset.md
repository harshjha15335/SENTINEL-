# SENTINEL — Follow the Money: creative reset

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

The user rejected both the reel metaphor and graphite/lime identity. This document supersedes the visual direction in documents 04, 05, 07 and 08. It does not authorize Phase 2, route cutover, legacy deletion or deployment.

## Scope and identity

Development-only `/__v2-preview`; branch `redesign/sentinel-v2`. Recovery checkpoint before reset: `bcbbc75ed09fc5045e1295b6b92612cb19f2bafc`, ref `backup/sentinel-v2-before-money-trail`. Verified full-history bundle: `/workspace/sentinel-money-trail/before-money-trail.bundle`. Restore into a new worktree with `git worktree add /workspace/SENTINEL-before-money-trail backup/sentinel-v2-before-money-trail`; do not reset an existing worktree.

Warm ivory #F7F4EE, ink #201A2B, purple #7547EB, coral #FF865C, lilac #D9D2E6. Surface white; alternate #EFEBF5; secondary text #686273; accent-soft #E9E0FF; border #DED7E5; critical #C33145; success #15745E; warning #986000. Critical pill background is sufficiently light for AA contrast. Coral uses ink labels. No lime accent.

Fonts are self-hosted open-source Fontsource packages: Manrope 400/600/700, DM Sans 400/500, IBM Plex Mono 400. Their package licenses remain in installed dependencies. No runtime third-party font requests. Original wallet, banknotes, receipt and containment artwork use SVG, authored in this repository; no reference illustration was imported. The wallet remains stylized vector artwork rather than photorealistic 3D.

## Animation contract

One desktop ScrollTrigger, `sentinel-money-trail`, 400% native scroll travel. No snapping, scroll interception, random paths, background animation loop or per-frame React state. `moneyScene(progress)` defines deterministic wallet placement, progressive fold opening, receipt travel, isolation and workspace assembly. Seven chapter starts: 0, .12, .27, .43, .57, .72, .90. Forward/backward samples return identical attributes. GSAP context reverts on route/unmount; breakpoint switches remount the compact/desktop scenes.

The purple wallet is the anchor. Two stylized banknotes and two demo receipts emerge. The $1,849 receipt remains the persistent narrative anchor; the $249 example continues along a separate authored path with its purple accent while the selected payment turns coral. The companion receipt and banknotes recede while the selected receipt slows, straightens, changes its accent to coral and is contained by a geometric field. Supported historical signals appear around it. Its $1,849 amount, seven prior-day payments, 8.4× median and 87/100 score come from authored, explicitly illustrative public fixtures. They do not establish actual detection, inference or intent.

The final receipt composition expands into the actual shared `DemoDossier` React component, not a screenshot. The inert visual preview fills the viewport; the final CTA opens the interactive instance at scrollY=0. Shared heading geometry is browser-tested. This is a coordinated layout expansion, not a per-field morph. The public demonstration opens a demo dossier; authorized records remain separately session-gated. `/` and `/app` migration remains pending.

Compact mobile/reduced-motion uses a readable unpinned vertical narrative, an above-fold CTA and a recognizable wallet. Normal mobile scroll opens the flap; reduced-motion leaves it still. A keyboard skip action focuses the after-story section. Mobile does not reproduce the desktop flying-object scene.

## Operational composition and implementation status

- Light horizontal global navigation. Compact native details menu on smaller screens. Supported existing Investigations, Risk Intelligence, Policy Lab, Monitoring and Account links open unchanged operational routes and are explicitly marked. No invented destinations or account/session logic.
- Command Center: interactive **composition prototype**, two SIMULATED examples. Priority exception, authored queue and example activity sequence; no live aggregate/operational queue claimed. Links work; no mutations.
- Transaction Explorer: existing session/API hooks; search/status/origin filters and pagination use existing query contracts. Current-page amount sort is explicitly labeled, not misrepresented as server sorting. Selection retains filters and opens real merchant-scoped transaction/risk/case data. Loading, empty, error, expiry and denial remain genuine states; no fixture fallback.
- Dossier: chronological evidence ledger, prominent amount/status/provenance, broad horizontal risk explanation, grouped transaction facts and full timeline controls. Model contributions retain actual pre-calibration log-odds labels and limitations. Demo values remain authored examples. Existing associated cases open unchanged workflows; all financial actions stay in existing screens.
- Full migration of operational screens and mutating workflows is deferred. The old application is preserved.

## Originality comparison

Old app: dark sidebar, dense boxed operational cards and grids. Rejected V2: dark rail, mono labels, stationary/mechanical reel and a split risk sidebar. New preview: warm open canvas, horizontal navigation, Manrope editorial hierarchy, softly rounded purple controls, chronological ledger and horizontal explanation strip. Command Center prioritizes a single example exception and review desk rather than equal KPI cards. Homepage uses financial objects rather than tape/machine transport. Business hooks and safety behavior are reused; presentation is replaced.

## Verification and limitations

See the delivery test report for exact commands, executed counts, SHA and evidence. Browser cases cover native scrolling/reverse, deterministic object state, refresh/history, shared layout entry, resize/pin cleanup, reduced motion, keyboard skip, seven viewport sizes, actual authorized API data/case links, errors/expiry, and accessible contrast audits. Font/preview emission is checked in normal and static production builds.

No test result grants artistic approval. Physical mobile devices, manual screen-reader operation, Firefox/WebKit and genuine external providers are outside the verified scope. Dev-executor frame timing is diagnostic only; do not infer field performance or sustained 60 FPS from the recordings. Build chunk warnings in the unchanged production application remain visible in logs.

Delivery directory: `/workspace/sentinel-money-trail/approval`.
Share ZIP: `/workspace/shared/downloads/SENTINEL-Follow-the-Money-approval.zip`.
