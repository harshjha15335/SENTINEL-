# Follow the Money — final Gate 1 polish

DESIGN APPROVAL: PENDING

DEPLOYMENT APPROVAL: PENDING

The user accepted Follow the Money as the preferred creative direction, subject to these visual corrections. This supersedes the scaled-workspace transition described in documents 09 and 10. It does not authorize Phase 2, route cutover, legacy removal or deployment.

## Recoverable starting point

Reviewed source: `10900c71d4cfe2072deb17b7834541e170ad9b70`.
Recovery ref: `backup/sentinel-v2-before-gate1-polish`.
Verified pre-polish bundle: `/workspace/sentinel-gate1-polish/before-polish.bundle`.
Restore safely into a separate directory with `git worktree add /workspace/SENTINEL-before-gate1-polish backup/sentinel-v2-before-gate1-polish`. Do not reset or clean an existing worktree.

## Actual visual changes

- Wallet: a visible central fold, shaded side gussets, leather grain, edge highlights, inner card pockets, bill compartment and three layered bills. The interior progressively appears as the flap opens; reduced-motion keeps the illustration still. Original layered SVG; no borrowed reference imagery, heavy 3D runtime or new dependency.
- Release: six curled banknotes instead of two flat notes. Each has an authored stagger, trajectory, size, rotation and mild perspective skew. Layers overlap intentionally around the wallet and receipts. Both authored receipts remain; the $1,849 selected receipt turns coral while the $249 companion remains purple and exits. No random motion, cash denomination claims or new detection logic.
- Transformation: the selected receipt stops at the known scene bounds. Its paper expands into the measured dossier-header bounds. The amount, record label and currency use native HTML text with interpolated position/font size, not scaled text. The product context appears within that growing paper. The amount reaches the actual shared dossier header, then a clip aperture unfolds outward to reveal the full-size, real React workspace. The embedded workspace and its typography never use a scale transform. No miniature website or screenshot is substituted.
- Layout measurement occurs on mount/font readiness/ScrollTrigger refresh, not every animation frame. Progress writes cached geometry and native text styles; React does not rerender per frame. Reverse scroll follows the same deterministic state.
- Readability: functional small labels and technical captions have an 11px CSS floor, including mobile provenance, casefile metadata and risk labels. Existing body/data hierarchy is retained.
- Glyphs: navigation arrows are Lucide SVG components; the unsupported arrow text glyph was removed from the receipt artwork. No dependency on a font containing that character remains in preview source.
- Entry clarity: public CTAs say **Explore simulated demo** or **Open the simulated dossier**. A separate **Open authenticated workspace** link appears in both desktop and mobile heroes and reaches the unchanged session-gated records preview. Demo entry is not presented as authentication or operational access.

## Scope retained

Palette, editorial typography, horizontal navigation, explorer/dossier architecture, existing API/session integrations, normal history restoration, mobile narrative and reduced-motion behavior remain. The Command Center remains an explicitly labeled two-example simulated composition prototype. It is not populated with fabricated live totals or promoted to an operational dashboard. Its actual-data migration belongs to Phase 2 after explicit approval.

No backend, ML, API contract, authentication, infrastructure or legacy-screen source changes. No push, merge or deployment.

## Verification and visual approval evidence

Share-safe logs and exact current SHA are in the delivered report. Checks include frontend typing/lint/tests, dedicated disposable-database backend regression, existing Chromium integration/responsive/accessibility tests, a new native-header morph test, normal/static production isolation and diagnostic frame timing.

The new browser test checks that workspace text and its container remain untransformed at four intermediate checkpoints, the carried amount aligns with the actual header, reverse sampling restores its geometry, and six banknotes exist. Existing tests retain actual session → API → PostgreSQL → dossier → existing case, error/expiry, filtering, mobile/reduced motion, keyboard skip, refresh/history and clean remount coverage.

The approval package includes seven desktop stages, 2× captures, four transition detail frames, native forward/reverse wheel-input recording, a separate final transformation/CTA recording, mobile views and direct before/after pairs against the reviewed 10900c7 checkpoint. Rendered captures and sampled recording frames are inspected in addition to test assertions.

## Limits

The wallet remains a stylized vector illustration, not a photorealistic leather simulation. Money artwork is metaphorical. The receipt transformation preserves the amount and header structure; it is not a morph of every provider field. The native workspace is revealed by a moving clip, so surrounding content deliberately appears after the payment header. Mobile uses the performant vertical story, not a desktop pinned cash burst.

No physical-device, Firefox/WebKit, manual screen-reader or genuine external-provider validation. Local headless dev timing does not establish sustained 60 FPS, production performance or field INP. Existing production chunk warnings remain visible. These limitations and test results do not grant design approval.

Delivery: `/workspace/sentinel-gate1-polish/approval/`.
ZIP: `/workspace/shared/downloads/SENTINEL-Gate1-visual-polish.zip`.
Final bundle: `/workspace/sentinel-gate1-polish/gate1-polish-checkpoint.bundle`.
