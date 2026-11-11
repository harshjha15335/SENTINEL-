# SENTINEL V2 acceptance-blocker remediation

Branch: `fix/sentinel-v2-acceptance-blockers` (local only), based on audited `8250671f202bfee5813518c52056492903d061df`. Exact final SHA and checksummed external artifacts are in the delivery report. PR #2 remains draft at 8250671; main remains 482985f. No push, PR update, merge, deployment or live provider call occurred.

## Result

CODE REMEDIATION: COMPLETE (local code corrections).
SOURCE AND DESIGN PRESERVATION: PASS (approved presentation retained; scoped logout/error semantics and callback corrections documented).
MAIN MERGE READINESS: BLOCKED (H02; PR #2 does not contain these local fixes).
DEPLOYMENT READINESS: BLOCKED (H02, hosted H01 acceptance, H03 approval/configuration and required hosted/provider checks).
LIVE-PROVIDER VALIDATION: NOT EXECUTED.

## Corrections and evidence

- S01: evidence-specific route checks session/CSRF/role/case merchant before multipart parsing; bounds declared and actual streamed request, each file and part count; no whole-request buffering; closes all temporary files on success, validation, disconnect, cancellation and truncated multipart. File size violations are documented 413; earlier business/tenant/PDF/storage rules remain.
- S02: clear session/cache only on completed logout or authoritative 401; failures remain truthful and retryable; revalidate expiry; accessible alert/retry and named account region. Successful logout produces server /me 401. No change to login/deep-link/history/permission semantics.
- S03: validate original URL before parsing, all whitespace/control characters, hostname/IP and port, credentials/scheme restrictions. Explicit hosted sandbox public HTTPS callbacks required. No DNS/provider request made.
- S04: return/cancel pages report receipt/unverified state, including browser titles; HTML escaping retained; CSP/no-store/no-referrer and mobile sizing; no financial mutation or provider verification on GET.
- H01: lock contention is interruptible standby, not a crash; graceful stop releases lock and finishes durable boundaries. Supervisor crash budget remains intact for real failures. Four process/lock regressions plus an isolated real scoring job survive owner death and duplicate enqueue with one assessment. Hosted rollout still unverified.
- H02: unresolved account evidence; see owner-verification-checklist.md. Render project link cannot be inspected with current access. No account settings changed.
- H03: hosting-proposal.md is review-only, fixture/no-AI/refund-disabled/manual, with migration, capacity, source pin, budget and rollback gates. No existing manifest was applied.
- N01/N02: see dependency-and-credential-review.md. No upgrades or historical credential validation/rotation was performed.

## Final local regression

356 backend pass / 1 credential-gated live-AI skip; 53 frontend pass; 7 ML pass; 34 auxiliary pass; 34 operational browser pass; 24 static browser pass. Total 508 pass, 1 skip: +54 API, +4 frontend, +8 browser = 66 new regressions over 442.

Formatting/lint/types, three builds, contract parity, schema checks on disposable databases, snapshot consistency, production boundaries, offline Postman and offline provider wire checks pass. Browser uses actual compiled API+SPA and CSP, not an older frontend. Five explicit viewports (1440x900,1366x768,768x1024,390x844,360x800), screenshots, reduced-motion/keyboard/current workflow regressions retained. Browser and automated accessibility evidence is not real-device or screen-reader certification.

Commands and environment details are in the external REPRODUCTION.md and runner scripts. Frontend final full run uses `npm test -- --maxWorkers=1` with unchanged five-second deadlines. Earlier default and serial runs had unchanged CaseDetailPage/login timeouts; isolated case diagnostic and final full serial run passed. Initial failures remain preserved, including aggregate-fixture setup, intermediate interrupted run for truncated cleanup, worker-observation setup, and initial Axe region findings. No assertions/deadlines/Axe rules were weakened.

Public story, design styles/fonts, models, training, migrations, payment/refund/webhook/investigation services and dependency pins are preserved. Contract diff only documents evidence 413. Existing large transaction-grid build warning remains; no unrelated redesign or optimization introduced.

## Review / publication boundary

Read hosting-proposal.md, owner-verification-checklist.md and rollback.md. Independent review precedes any separately authorized publication/PR action. PR #2 remains the unfixed original candidate until a future authorized update. New remote workflows have not run because pushing is prohibited. No merge or deployment approval follows from passing local tests.
