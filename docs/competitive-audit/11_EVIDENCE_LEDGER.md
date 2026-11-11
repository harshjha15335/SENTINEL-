# 11 — CENTRALIZED EVIDENCE LEDGER: SENTINEL VS FRAUD RISK MANAGER

**Audit Scope:** Two-Stage Forensic Audit Ledger  
**Audit Date:** November 11, 2026  

---

## 1. EVIDENCE AND PROVENANCE MATRIX

| Claim ID | Subject Project | Dimension / Claim | Primary Evidence Source | Line / Path Citation | Confidence | Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `LED-001` | SENTINEL | PayPal Orders v2 Capture ($25) | Local PostgreSQL DB & PayPal GET | `orders.provider_order_id = 2PE07332LD3413239` | High | **VERIFIED WORKING** |
| `LED-002` | SENTINEL | Local Transaction State (`CAPTURED`) | Local PostgreSQL DB | `transactions.id = b970504f-274f-4862...` | High | **VERIFIED WORKING** |
| `LED-003` | SENTINEL | Calibrated Risk Assessment (0.0869) | Local PostgreSQL DB | `risk_assessments.id = dae7c7f2...` | High | **VERIFIED WORKING** |
| `LED-004` | SENTINEL | Full Backend Test Suite Passing | Pytest command output | 302 passed, 1 skipped in 278.54s | High | **VERIFIED WORKING** |
| `LED-005` | SENTINEL | Frontend Vitest Component Suite | Vitest command output | 39 passed in 21.46s | High | **VERIFIED WORKING** |
| `LED-006` | SENTINEL | Full File Census Audit (100%) | `docs/competitive-audit/sentinel-first/S01_FILE_CENSUS.csv` | 390 tracked files audited | High | **VERIFIED WORKING** |
| `LED-007` | SENTINEL | Linear Migration Chain (`d105a4143283`)| `apps/api/alembic/versions/` | 6 migration files verified | High | **VERIFIED WORKING** |
| `LED-008` | SENTINEL | Native JSON Booster (No Pickle) | `apps/api/app/risk_models/operational-v1/booster.json` | 114,458 bytes, SHA256 verified | High | **VERIFIED WORKING** |
| `LED-009` | FRM | Vercel Frontend Availability | Public HTTP GET request | `https://fraud-risk-manager.vercel.app/` (HTTP 200) | High | **VERIFIED WORKING** |
| `LED-010` | FRM | Render Backend Cold Start Timeout | Public HTTP GET request | `https://fraud-risk-manager.onrender.com/openapi.json` | High | **TIMEOUT > 50s** |
| `LED-011` | FRM | Discovered Endpoint Registry (8) | JS Bundle lexical analysis | `assets/index-B6pZVuKT.js` (1.94 MB) | High | **VERIFIED FROM BUNDLE** |
| `LED-012` | FRM | Zero PayPal Integration Code | Lexical scan of JS Bundle & API | Zero PayPal endpoints, zero SDKs | High | **NOT IMPLEMENTED** |
| `LED-013` | FRM | Zero Generative AI / Agent Code | Lexical scan of JS Bundle & API | Zero LLMs, zero Gemini/OpenAI calls | High | **NOT IMPLEMENTED** |
| `LED-014` | FRM | Zero Authentication / RBAC | Lexical scan of JS Bundle & API | Zero login routes, zero tokens | High | **NOT IMPLEMENTED** |

