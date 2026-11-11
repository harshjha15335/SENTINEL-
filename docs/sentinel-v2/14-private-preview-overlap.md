# Private review preview — dossier entry overlap correction

The user requested a reachable review preview on 10 November 2026, then reported that its floating entry CTA covered the revealed dossier. The owner-private read-only Site is `appgprj_6af2d2f4d6fc8191b09313e4fc3ae64b`; its source is isolated under `/workspace/sites/sentinel-v2-review-20261110`, separate from SENTINEL's GitHub remote. Updating this private review copy is authorized. Operational deployment/Gate 2 remains PENDING.

The entry CTA now occupies a normal-flow row after the pinned story rather than an absolute overlay on the dossier. It cannot cover the payment amount, status, origin, date or timeline. The final native dossier frame and its typography are unchanged. Keyboard focus can scroll to the entry row when the last chapter is selected.

Navigation applies the requested scroll position before paint as well as on the next frame. This prevents an effect replay from preserving the outgoing story's scroll position when opening the dossier. Existing POP/reload and same-path query restoration remain.

Five browser regressions assert non-intersecting reveal/action bounds and top-of-page entry at 1890×652 (the reported short viewport), 1440×900, 1280×720 1024×768 and a 945×326 layout for a heavily zoomed/short window. They join the retained scene, mobile, reduced-motion, history and API integration suite. Verification logs and screenshots are under `/workspace/sentinel-overlap-fix` and `/workspace/sentinel-phase2/evidence/overlap-*`.

The original Phase 2 review ZIP remains the historical delivery at its recorded checkpoint. The current private preview and this correction have a separate local source commit and follow-up report; do not describe the original archive as regenerated for this correction. No backend, contracts, database schema, ML, provider settings or GitHub branch publication changes are part of this fix.
