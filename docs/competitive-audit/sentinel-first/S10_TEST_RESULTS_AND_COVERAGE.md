# S10 — TEST RESULTS, EXECUTION EVIDENCE, AND COVERAGE AUDIT

**System:** SENTINEL Test Architecture  
**Test Frameworks:** Pytest 9.1.1, Vitest 5.0.3, TypeScript 5.x Compiler  
**Audit Verification:** Executed directly in local environment  

---

## 1. AUTOMATED TEST SUITE EXECUTION SUMMARY

| Test Suite | Execution Command | Result | Duration | Scope & Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Full Backend Suite** | `pytest apps/api/tests` | **302 PASSED, 1 SKIPPED** | 278.54s | Complete API, database, auth, and worker coverage |
| **Core Invariant Suite** | `pytest apps/api/tests/test_risk_cases.py ...` | **107 PASSED** | 146.25s | Core platform, scoring, webhooks, investigations |
| **Inbox Bridge Invariants**| `pytest apps/api/tests/test_supabase_inbox.py`| **14 PASSED** | 16.55s | Receipt verification, lease isolation, retry backoff |
| **ML Pipeline Suite** | `pytest ml/tests/test_pipeline.py` | **7 PASSED** | 41.65s | Dataset split, feature transforms, XGBoost booster |
| **Deployment Contract** | `pytest deploy/tests/test_render_contract.py` | **2 PASSED** | 0.41s | Render Blueprint schema & contract verification |
| **Frontend Unit Tests** | `npm --prefix apps/web test` | **39 PASSED (13 files)** | 21.46s | Component rendering, user interaction, states |
| **Frontend Typecheck** | `npm --prefix apps/web run typecheck` | **0 ERRORS** | 3.50s | Strict `tsc -b --noEmit` compilation |
| **Frontend Production Build**| `npm --prefix apps/web run build` | **SUCCESS** | 1.99s | Optimized Vite production bundle in `dist/` |
| **Static Code Linter** | `ruff check apps/api scripts` | **0 ERRORS** | 0.85s | Python syntax, import order, unused symbols |

---

## 2. SKIPPED TEST AUDIT & RATIONALE

- **Skipped Test:** `apps/api/tests/test_hosted_database_tls.py::test_hosted_database_enforces_tls`
- **Reason:** Designed specifically for remote staging/production databases (`SENTINEL_DATABASE_URL` with `sslmode=require`). Skips gracefully in local developer SQLite/Postgres environments where remote TLS certificates are not mounted.

---

## 3. TEST ASSERTION QUALITY & MOCK AUDIT

- **No False Asserts:** Assertions verify persistent database state via SQLAlchemy sessions rather than simply asserting on HTTP return codes.
- **Strict Webhook Cryptographic Verification:** Webhook tests in `test_webhooks.py` validate real RSA SHA-256 signatures against mock certificates, verifying that invalid signatures, altered bodies, or forged transmission times are rejected with `HTTP 400/401`.
- **Durable Scoring Idempotency Assertions:** Tests in `test_scoring_jobs.py` explicitly assert that submitting duplicate webhook events reuses existing `RiskAssessment` records without triggering redundant ML inference.

