# Migration progress

| Milestone | Status | Evidence |
|---|---|---|
| Inspect main and preserve recovered features | Complete | Baseline 410109c, feature/action/state/server route inventory |
| Isolate branch/checkpoint | Complete | redesign/sentinel-v2; verified baseline ref/bundle |
| Establish scoped design prototype | Complete for review | preview.css, Machine, Story, Dossier, labeled fixtures |
| Verify representative workflow | Complete locally | Authenticated API/DB dossier → existing case; explicit error/empty/expiry checks |
| Verify responsive/reversible scene | Complete in Chromium | Six checkpoints, reverse/refresh/remount, resize, mobile and reduced motion |
| Design and route approval | PENDING | Gate 1 requires explicit user approval |
| Replace application screens | NOT STARTED | Existing screens retained |
| Complete public homepage/machine-to-workspace polish | NOT STARTED beyond prototype | Phase 2 scope |
| Remove legacy presentation | NOT STARTED | Only after replacement parity and approval |
| Final accessibility/performance/cross-browser release review | NOT COMPLETE | Prototype measurements and bounded checks only |
| Deployment approval / deployment | PENDING / NOT PERFORMED | Gate 2 requires separately scoped authorization |

The preview's case link deliberately opens the existing case page; it is not a claim that Investigation Room has been redesigned. Backend evidence/approval functionality remains available and separately regression-tested. No optional product capability was added to satisfy a marketing checklist.

Source changes: five exact frontend dependencies; DEV-only preview import/route in App.tsx; six new preview source files; two browser test files and a separate config; two verification scripts; project guidance and these documents. No legacy page deletion, API/ML changes, route cutover, production infrastructure change, push or deployment.
