# 01 — SENTINEL CODEBASE AND ARCHITECTURAL AUDIT

**Target:** SENTINEL Codebase (`C:\Users\ranja\Sentinel\SENTINEL-`)  
**Commit SHA:** `3072f185042a6bcd1fdada294248bf8bba2426c4` (tag: `v2.0.0-rc1`)  
**Census Baseline:** [S01_FILE_CENSUS.csv](sentinel-first/S01_FILE_CENSUS.csv) & [S02_FILE_BY_FILE_AUDIT.csv](sentinel-first/S02_FILE_BY_FILE_AUDIT.csv)  

---

## 1. COMPREHENSIVE ARCHITECTURAL ANALYSIS

SENTINEL is structured as an enterprise-grade payment fraud intelligence and investigation platform:

```
SENTINEL Core Topology:
├── apps/
│   ├── api/          # FastAPI 0.143.0 backend, SQLAlchemy ORM, Uvicorn, background workers
│   │   ├── app/      # Business logic: auth, checkout, paypal, webhooks, cases, risk, investigations
│   │   └── tests/    # 35 test files covering 303 automated test cases
│   └── web/          # React 19 + TypeScript + Vite SPA
│       └── src/      # 13 feature modules: cases, checkout, dashboard, disputes, policy, refunds, risk
├── ml/               # Machine learning pipelines, synthetic dataset generators, holdout evaluations
├── supabase/         # Edge function receiver and durable PostgreSQL webhook inbox
├── deploy/           # Render Blueprint manifests, contract verification tests
└── scripts/          # Operational, inspection, verification, and recovery runbooks
```

---

## 2. KEY ARCHITECTURAL ADVANTAGES

1. **Single-Origin Deployment Architecture:**
   - Multi-stage Docker container serves the built Vite frontend (`apps/web/dist`) directly from FastAPI on port `8000`. Eliminates all production CORS issues, cookie mismatch issues, and multi-domain latency.
2. **PostgreSQL Advisory Lock Process Supervision:**
   - Background pipeline worker uses advisory lock `7682346` to guarantee single-consumer job execution even across dynamic worker reboots.
3. **Dual-Path Scoring Idempotency:**
   - Real-time scoring executes synchronously on capture (`score_after_capture()`), while asynchronous webhook processing (`RiskScoringJob`) detects existing assessments and prevents redundant evaluations.
4. **Strict Multi-Tenant Scoping:**
   - Enforced at ORM query boundaries: `WHERE merchant_id == principal.merchant_id`. Eliminates BOLA / IDOR vulnerabilities.

