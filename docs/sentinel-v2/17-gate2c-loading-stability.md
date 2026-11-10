# Gate 2C — targeted loading stability

DESIGN APPROVAL: APPROVED

DEPLOYMENT APPROVAL: PENDING

Starting source: `a42f396c4950cbc46abf942e6d092979d5ff9eda`. Recovery ref: `backup/sentinel-v2-before-gate2c`; full pre-change bundle `/workspace/sentinel-gate2c/before.bundle`. No push, merge, hosting resources, publication, sharing changes or deployment is authorized.

## Diagnosis

Gate 2B's exact cache-disabled, cold-browser/warm-loopback HTTPS lab was reproduced on the preserved original artifact. Maximum CLS reproduced at 0.315 desktop / 0.575 simulated mobile for Transactions and 0.0815 / 0.2402 for recorded Risk; homepage remained zero. Unrounded samples are retained in `/workspace/sentinel-gate2c/evidence/before-performance.json`. An earlier run that overlapped diagnostic capture is labelled preliminary and is not the controlled comparison.

Separate Chromium/CDP screencasts, Layout Instability sources/rectangles, resource timings, font events and layout-box timelines are retained in `before-diagnostics/`. They identify late banner insertion shifting the account bar/main/footers, generic short lazy/data placeholders replacing much taller records, and AG Grid auto-height expansion from its loading state to all 25 rows. Pagination/footer attribution rectangles disappear when moved beyond the visible viewport, not because records were removed. Late Manrope loads also moved heading/timeline text by several pixels.

## Small frontend correction

- Render the read-only banner synchronously with the shell. Its export-date slot has a stable monospace width during metadata loading; genuine timestamps/provenance and unavailable-date errors remain truthful.
- Start the existing workspace font faces loading during the existing session-loading state using FontFaceSet. Nothing waits for fonts before rendering. This is scoped to the app shell: public Follow the Money pages do not fetch merchant data or warm workspace fonts. Direct font-face activation avoids duplicate font preload transfers in the cache-disabled lab.
- Give lazy-route/data placeholders the same record structure and meaningful reserved space. The payment skeleton keeps the backlink, record-header, timeline, risk and references geometry; transaction placeholders follow the responsive toolbar/grid shape. These are loading placeholders, never fake amounts, scores or events.
- Give the grid a predictable responsive viewport and preserve AG Grid's native scrolling. The page still contains the original 25 rows, all columns, sorting, filters, search, pagination and Enter handling. Keep the 25-row page mounted: row virtualization otherwise dropped keyboard focus when moving from the last row back to the first. Home/End and keyboard entry are regression-tested.
- Reserve the observed six-factor risk content footprint and timeline area; retain normal growth for longer content. No chart, factor, record or field is removed or clipped. Unscored/error content remains compact. Fix section-title line height to avoid fallback-font line-box changes.

There are no changes to backend logic, models, contracts, migrations, session/authentication decisions, payments/refunds/approvals, data hooks or the approved homepage source. No page is concealed, no layout observer is altered, and no synthetic input is generated to exclude shifts. The data snapshot is reused byte-for-byte with 9,064 transactions, 1,824 assessments and 179 cases.

## Verification and release

`hosting/cloudflare-pages/stability-lab.mjs` records every sample, raw layout-shift attribution, observed LCP, readiness, transfer sizes, fonts, long tasks, grid wrapper/row timing and unexpected requests. Controlled profiles match Gate 2B; stress adds 100ms latency, 1.6Mbps download, 0.75Mbps upload and 4× CPU slowdown. It retains both the original 500ms-after-readiness observation and a longer 2s observation; target checks use the longer window, with no suppressed entries. Grid mount-to-rows includes data wait/rendering and is explicitly not isolated AG Grid CPU time.

The local host suite includes delayed-data geometry checks and native table keyboard coverage. Frontend unit, static/CSP/accessibility and operational workflow regressions, all three builds, exact snapshot closure, package checksums/privacy, compression/ETag and recovery checks are required before delivery. Reviewed `_headers`/`404.html` remain unchanged; fonts, scripts, CSS and JSON remain same-origin and keep their established cache classes. Host preparation must pin the newly verified static package rather than the old Gate 2A archive.

Final measured results, exact source revisions, files changed, artifacts and limitations are recorded in `/workspace/sentinel-gate2c/REPORT.md` when verification is complete. Local lab results do not establish field Core Web Vitals, physical-device performance, broader browser coverage or actual Cloudflare edge/TLS behavior. The existing private review Site remains unchanged; stop before publication.
