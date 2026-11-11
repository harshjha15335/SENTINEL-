# 08 — TESTING, QUALITY ENGINEERING, AND DEPLOYMENT AUDIT

**Comparison:** Test Coverage, Reliability Engineering, and Deployment Topology  
**Auditor:** QA Automation Lead & SRE Engineer  

---

## 1. QUALITY ENGINEERING & TEST SUITES

| Quality Dimension | SENTINEL (Ours) | Fraud Risk Manager (Competitor) | Winner & Evidence |
| :--- | :--- | :--- | :---: |
| **Backend Unit & Integration** | **302 PASSED, 1 SKIPPED** (Pytest) | ~45 reported unit tests (unverified) | **SENTINEL** (Directly verified, 278.54s execution). |
| **Frontend Unit & Component** | **39 PASSED** (Vitest 5.0.3) | Unobservable | **SENTINEL** (13 test files testing DOM rendering). |
| **Bridge & Lifecycle Invariants**| **14 PASSED** (Lease locks, ACK) | 0 tests (No worker bridge) | **SENTINEL** (Receipt matching invariants proven). |
| **ML Pipeline Reproducibility** | **7 PASSED** (Feature transforms) | Unobservable | **SENTINEL** (7 tests in `ml/tests/test_pipeline.py`). |
| **Static Code Quality** | **0 Errors** (Ruff across all files) | Unobservable | **SENTINEL** (Ruff checks pass 100%). |
| **Typecheck Verification** | **0 Errors** (`tsc -b --noEmit`) | Unobservable | **SENTINEL** (Strict TypeScript compilation). |

---

## 2. DEPLOYMENT & RUNTIME TOPOLOGY

```
+---------------------------------------------------------------------------------------------------------------+
|                                            DEPLOYMENT COMPARISON                                              |
+------------------------------+---------------------------------------+----------------------------------------+
| Dimension                    | SENTINEL (Ours)                       | Fraud Risk Manager (Competitor)        |
+------------------------------+---------------------------------------+----------------------------------------+
| Deployment Target            | Single Docker Container (Render)      | Split: Vercel (Web) + Render (API)     |
| Origin Architecture          | Single Origin (:8000)                 | Cross-Origin (Vercel -> Render)        |
| CORS Exposure                | Zero (Same-origin API & SPA)          | High (Permissive CORS headers required)|
| Cold-Start Resilience        | Supervised workers, `/ready` probe    | Observed timeout >50s on free Render   |
| Persistence Model            | Managed PostgreSQL + Alembic          | Local disk SQLite (wipes on restart)   |
| Public Demo Status           | Local release ready, tagged v2.0.0-rc1| Public Vercel frontend live            |
+------------------------------+---------------------------------------+----------------------------------------+
```

### Critical SRE Insight:
Fraud Risk Manager's split deployment exposes it to cross-origin CORS issues and cold-start failures. In our passive audit, probing FRM's backend timed out after 50 seconds due to Render free-tier sleep. SENTINEL's single-container design hosts the built web assets and the API under one Uvicorn process, completely eliminating cross-origin latency and configuration fragility.

