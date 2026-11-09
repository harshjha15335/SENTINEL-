# Phase 1 visual corrections — review pending

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

The user accepted the technical foundation at `53c42953cd9fb99ed0af4ced3238e2c6317873b9` but explicitly requested visual changes. This correction pass does not authorize Phase 2, route cutover, legacy removal or deployment.

Source checkpoint: `4f1954f9cb1d5d8ac53c896b5fdcd5a85be65234`.

## Reference comparison

The supplied `Wispr_Flow_scroll_reference_trimmed.mp4` downloaded successfully (10,476,425 bytes, 90 seconds, 464×858). I inspected frame sequences across the clip and the unfolding sequence around 28–50 seconds. It shows a photographed/filmed browser experience: the cassette is a physical anchor, a strip exits it, the cassette recedes, and the strip carries story content through broad curves. Our previous “unable to inspect reference” limitation is resolved.

| Reference principle | Correction implemented | Evidence to inspect |
|---|---|---|
| Physical object anchors the opening | Refined original housing, metal flanges/hubs, wound packs, output port and scanner | Updated idle/activation screenshots |
| Object changes scale and composition | Continuous housing translation, rotation and recession from p=.14 onward | Six checkpoints and forward/reverse video |
| Tape leaves the object | Path begins at the mathematically transformed output port; alignment checked in browser | Tape/port test and signals screenshot |
| Strip carries story content | Transaction and signal frames attach to points on the same curved strip; no independent popup panels | Signals/risk stages |
| Evidence becomes product content | Strip straightens, risk context resolves and actual shared React dossier expands into the final composition | Focused transition recording |
| Continuous entry into workspace | Source/destination use the same component and heading location; route opens at scrollY=0 | Handoff/history browser test |

This borrows the interaction principle only. It does not copy the purple cassette, pencil, photos, portfolio content, page composition or branding. Visual equivalence and quality are not implied by technical test results.

## What changed

- Rebuilt only the development-only Evidence Reel presentation and its preview navigation behavior.
- Added a continuous path/reveal mask, attached evidence frames and path-sourced illustrative risk graphic.
- Introduced conserved wound-pack geometry and integrated rotation at changing radius; original fixture values are retained.
- Reused DemoDossier for the scene's final live HTML layout, with no screenshot substituted for working UI.
- Fixed CTA entry to top and added preview-scoped history/reload restoration.
- Added a visible mobile CTA above the machine, legible HTML content, a continuous vertical evidence thread and an unpinned hero transport effect.
- Preserved graphite/ivory/lime identity, typography, API/session hooks, two fixtures and accessible controls.

No backend, contract, ML, production route, old screen, deployment configuration or dependency version was changed. Recovery ref `backup/sentinel-v2-before-visual-corrections` and verified bundle `/workspace/sentinel-v2-revision/before-corrections.bundle` preserve the exact prior prototype.

## Verification

- Frontend: 43 unit tests passed (original 39 plus four physical-model tests); typing and lint passed.
- Backend: fresh run against separate loopback `sentinel_visual_revision_test`: 262 passed, 1 real-provider skip. Existing preview data was not truncated.
- Chromium: final isolated run passed 17 tests, including the original preview/integration flows, tape reversal/port alignment, shared-layout CTA/direct/refresh/back/forward, mobile CTA/transport, reduced motion, resize, overflow and duplicate-pin checks.
- Normal and static/hash production builds passed; production isolation smoke check reports no preview root, asset requests or emitted preview assets.
- Axe scans ran as part of browser checks. No full WCAG conformance claim or physical-device/manual-screen-reader validation.
- A concurrent browser run collided on its temporary trace directory. The complete final run used its own output directory and passed; the failed run is not counted as a success.
- Genuine providers and production operations were not exercised. Firefox/WebKit remain unverified due the earlier download-policy blocker.

## Visual review and limits

The source/destination are the same real layout. Source preview controls are intentionally inert; the CTA opens the interactive version. The final frame's floating CTA disappears on navigation, while the dossier composition stays aligned. This is a shared-layout handoff, not an invented backend investigation or per-element photorealistic morph.

The machine is more detailed but remains stylized SVG. The tape's widening into content is a narrative abstraction. On mobile, the hero reels respond to scroll but the full desktop spatial choreography is replaced by a normal vertical narrative. Dense metadata still warrants user review at normal zoom. Cross-browser polish and real-user performance remain outside this local approval verdict.

The new ZIP includes six desktop stages (1× and 2×), forward/reverse and final-entry MP4s, mobile reel/workspace, current dossier, before/after captures, reference comparison, test logs, source identity and this handoff. No credentials or authentication traces belong in the shareable archive.

Full application migration has NOT started. The user must review the new experience before Gate 1 can be approved. The `/` public homepage and protected `/app` proposal remains unchanged and unapproved.

## Lab performance limitation

The larger spatial SVG is heavier than the original stationary illustration. Initial dev lab observations showed median frame intervals near 33.3ms and occasional >50ms frames. Per-frame SVG length/point reads were replaced with analytical Bezier evaluation and approximate arc-length sampling; viewport dimensions are cached at refresh. This removes synchronous geometry queries from the scroll renderer, but is not proof of a sustained 60 FPS result. The final lab measurements are in the shareable package's PERFORMANCE.json. They are unthrottled localhost measurements on a shared headless cloud executor, not field INP or production p75 data. Performance remains an explicit review limitation; no production-readiness claim is made.
