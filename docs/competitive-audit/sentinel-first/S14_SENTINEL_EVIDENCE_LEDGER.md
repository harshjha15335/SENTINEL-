# S14 — SENTINEL EVIDENCE LEDGER

**Audit Milestone:** PART I Standalone Evidence Provenance  
**Audited Commit:** `3072f185042a6bcd1fdada294248bf8bba2426c4`  

---

## 1. EVIDENCE CITATION LEDGER

| Evidence ID | Claim / Dimension | Source Location | Exact Line / Reference | Verification Output |
| :--- | :--- | :--- | :--- | :--- |
| `EVD-001` | PayPal Orders v2 Capture | `apps/api/app/services/paypal/sandbox.py` | L210–245 | Captured Order `2PE07332LD3413239`, Capture `8P799281C8558761R` |
| `EVD-002` | Local Transaction Record | Application PostgreSQL DB | `transactions` table | ID `b970504f-274f-4862-b95f-b95342002421`, status `CAPTURED` |
| `EVD-003` | XGBoost Risk Assessment | Application PostgreSQL DB | `risk_assessments` table | ID `dae7c7f2-af13-4352-8f96-cbb74c2b02d6`, score `0.0869`, band `MEDIUM` |
| `EVD-004` | Scoring Job Deduplication | Application PostgreSQL DB | `risk_scoring_jobs` table | ID `b27c85dc-4d62-4aba-97c9-da57a43557a5`, status `COMPLETED` |
| `EVD-005` | Reconciled Webhook 1 | Application PostgreSQL DB | `payment_events` table | ID `c4637f51`, type `CHECKOUT.ORDER.APPROVED` |
| `EVD-006` | Reconciled Webhook 2 | Application PostgreSQL DB | `payment_events` table | ID `65d36059`, type `PAYMENT.CAPTURE.COMPLETED` |
| `EVD-007` | Reconciled Webhook 3 | Application PostgreSQL DB | `payment_events` table | ID `293db5f7`, type `CHECKOUT.ORDER.COMPLETED` |
| `EVD-008` | XGBoost Model Booster | `apps/api/app/risk_models/operational-v1/booster.json` | 114,458 bytes | Native JSON booster, SHA256 `fb2e1e2c...` (No pickle) |
| `EVD-009` | Model Platt Calibration | `apps/api/app/risk_models/operational-v1/metadata.json` | L51–57 | Formula: `1 / (1 + exp(a * p_raw + b))`, a = -5.6291, b = 5.5534 |
| `EVD-010` | Full Backend Pytest Suite | PowerShell command execution | `pytest apps/api/tests` | `302 passed, 1 skipped in 278.54s` |
| `EVD-011` | Core Platform Pytest | PowerShell command execution | `pytest apps/api/tests/test_risk_cases.py ...` | `107 passed in 146.25s` |
| `EVD-012` | Inbox Bridge Invariants | PowerShell command execution | `pytest apps/api/tests/test_supabase_inbox.py` | `14 passed in 16.55s` |
| `EVD-013` | ML Pipeline Test Suite | PowerShell command execution | `pytest ml/tests/test_pipeline.py` | `7 passed in 41.65s` |
| `EVD-014` | Frontend Vitest Suite | PowerShell command execution | `npm --prefix apps/web test` | `39 passed across 13 test files in 21.46s` |
| `EVD-015` | Frontend Typecheck | PowerShell command execution | `npm --prefix apps/web run typecheck` | `tsc -b --noEmit` exited with code 0 |
| `EVD-016` | Frontend Production Build | PowerShell command execution | `npm --prefix apps/web run build` | Vite built in 1.99s to `apps/web/dist` |
| `EVD-017` | Linter Cleanliness | PowerShell command execution | `ruff check apps/api scripts` | All checks passed (0 errors) |
| `EVD-018` | Render Deployment Contract| PowerShell command execution | `pytest deploy/tests/test_render_contract.py` | `2 passed in 0.41s` |

