# Evidence Reel — revised spatial motion contract

This supersedes the stationary-machine prototype at `53c4295`. Design and deployment approval remain PENDING. The user's reference is now available and was visually inspected: the 90-second trimmed recording shows a physical cassette becoming a curved filmstrip that carries content through the page. The key sampled unfolding sequence is approximately 28–50 seconds into the supplied clip. No original cassette art, branding, photographs or composition was copied.

## One continuous scene

Source: `Story.tsx`, `Tape.tsx`, `Machine.tsx`, `scene.ts` and `story.css` under `apps/web/src/preview`. One desktop ScrollTrigger, ID `sentinel-evidence-reel`, controls a 1440×900 normalized SVG coordinate system and a shared React workspace layer. The scene pins for four viewport-heights of travel; the opening viewport makes five viewport-heights overall. No audio, autoplay, snapping or wheel interception.

Stages retain normalized boundaries 0 / .14 / .30 / .48 / .66 / .84 / 1:

1. Full-size machine and headline, stationary transport.
2. Transaction transport begins, diagnostic illumination, changing wound packs.
3. The housing tilts/recedes; a continuous strip emerges from its physical output port. Transaction/signal frames are attached to sampled points on the same path and appear only once the revealed strip reaches them.
4. The strip reaches an explicitly illustrative 87/100 risk visualization. The risk arc fills deterministically as the path completes.
5. Curved path coordinates straighten into an ordered evidence arrangement. The real HTML dossier expands from that composition; old narrative layers recede.
6. The same `DemoDossier` React component used by the destination fills the viewport. It is a live DOM layout preview, not a screenshot. A separate accessible CTA opens its interactive route at scrollY=0, preserving the heading composition.

The embedded preview is inert and hidden from the accessibility tree. Its first fixture is fixed so unrelated root query parameters cannot change the narrative's data. The actual destination retains both selectable fixtures and working tabs. Static/reduced-motion narrative text and the workspace CTA provide the accessible alternative.

## Physical transport

Uniform-thickness tape approximation: normalized advance `a = clamp((p-.14)/.70)`, distance `d=2600a`; inner radius 48, outer 92, cross-section difference A=92²−48².

- Supply radius: sqrt(92²−aA).
- Take-up radius: sqrt(48²+aA).
- Supply angle: −2·2600/A·(92−supply radius), radians.
- Take-up angle: −2·2600/A·(take-up radius−48), radians.

Thus the total wound cross-section is conserved, angular speeds vary with radius, both reels share tape distance and reversing p rewinds the same geometry. Metal flanges have real SVG cutout masks so the wound pack is visible. Tape endpoints inside the transport follow pack radii. Beveled housing edges, brushed-metal gradients, hub highlights, guide/exit fittings, scanner and layered contact shadows improve depth without new dependencies.

`placement()` transforms the housing. `evidencePath()` uses its transformed local port (763,380) as the start of the external strip. A browser geometry assertion verifies the two screen-space points stay within .1px. A reveal mask clips moving markings to the exposed strip. Frames are placed with getPointAtLength on that exact path; they are not independent overlays at arbitrary screen coordinates.

Rendering updates SVG attributes and CSS transforms/opacity outside React state. GSAP context cleanup removes pinning and triggers. Font readiness and resize refresh geometry; media-query subscription mounts either desktop or compact composition, never both machines simultaneously.

## Navigation and restoration

`PreviewNavigation.tsx` stores preview scroll positions by history key/path. Preview route changes open intentionally at the top; POP/reload restore saved positions. Same-path query changes preserve scroll. This behavior is inside the development-only preview and does not alter existing application routing/authentication. Tests cover the actual reel CTA, source/destination heading positions, direct entry, refresh at 150px, browser back to final story and forward to the saved dossier position.

## Mobile and reduced motion

At <=900px the headline, supporting copy and a primary workspace CTA precede the recognizable machine in the first viewport. Technical micro-labels are suppressed on narrow screens; essential text is ordinary HTML. A short unpinned hero ScrollTrigger operates the reels while that hero is visible. Its output connects through a curved strip to a readable vertical evidence sequence and shared dossier layout preview. No desktop pinning is used.

With reduced motion, the compact narrative remains readable and no transport trigger runs. Live media-query changes remove that trigger. Native keyboard controls and Skip story remain available; entering the final desktop chapter moves focus out of the now-inert chapter footer to the workspace CTA.

## Limits

This remains an original SVG interpretation, not photorealistic simulation. Full portfolio-style horizontal content browsing from the reference is not copied. The shared-layout handoff is coordinated expansion plus route entry, not a unique per-character or per-row morph. Final visual approval is the user's decision.
