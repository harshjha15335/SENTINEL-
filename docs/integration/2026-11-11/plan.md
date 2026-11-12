# Integration plan — 11 November 2026

UI: redesign/sentinel-v2 `dd5e790ca2273598b3eecd40d473d8f567aa98bc`. Implementation: GitHub main `482985f9cfc1ceee8cda9e700b959602874c494e`; fix/gemini-400-recovery points to its implementation parent3072f18. Common baseline `410109c9304e11d2e1e685600194e290d978c0ab`. UI27 commits /implementation14 commits since baseline. Main includes the complete newer implementation and competitive audit; use it as first parent.

See file-conflict-matrix.csv for the complete 250-path inventory, statuses, source hashes and resolution plan. Overlap: []. No shared edited files; semantic interfaces still require tests.

Create unique immutable refs and a full recovery bundle, then add a new isolated worktree from current GitHub main. Merge the UI source preserving both histories. Do not modify either source or main. Preserve API hooks, auth/CSRF/roles, score/calibration artifacts, schemas, migrations and provider semantics. Frontend dependencies come only from UI (implementation leaves package/lock unchanged); use npm ci. Backend dependencies unchanged from baseline.

Validate frontend lint/types/tests/builds, backend formatting/lint/types/full fixture tests, ML and bridge/deployment/script suites, OpenAPI drift/migrations, desktop/mobile operational and static browser suites with fixture-only disposable loopback databases. No live provider calls, recovery scripts or remote SQL. Source PayPal return HTML is backend-owned and requires visual/semantic review alongside the new UI.

Only push the new integration branch and open a draft PR. Main and source heads remain unchanged. READY FOR REVIEW requires all applicable gates passed; preserve blockers and exact failures. No deployment.
