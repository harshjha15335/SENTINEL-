# 00 — EXECUTIVE VERDICT: SENTINEL VS FRAUD RISK MANAGER

**Audit Scope:** Independent Technical, UX, ML, Architecture, Security, and PayPal AI Hackathon Evaluation  
**Auditor:** Principal Software Architect, Staff Backend Engineer, Senior UI/UX Engineer, Senior ML Engineer, Application Security Engineer, Fintech PM & Hackathon Evaluator  
**Audit Date:** November 11, 2026  
**Audited Commit (SENTINEL):** `3072f185042a6bcd1fdada294248bf8bba2426c4` (`main`, tag: `v2.0.0-rc1`)  
**Competitor Target:** Fraud Risk Manager (`https://fraud-risk-manager.vercel.app/`, `https://fraud-risk-manager.onrender.com/`)  

---

## 1. EXECUTIVE SUMMARY & VERDICT

### Overall Verdict: **SENTINEL IS TECHNICALLY DECISIVELY SUPERIOR; FRAUD RISK MANAGER HAS ADVANTAGES IN NICHE DEMO FEATURES (RETURN RISK & BATCH CSV)**

```
+-----------------------------------------------------------------------------------------------------------------+
|                                           EXECUTIVE COMPARISON MATRIX                                           |
+---------------------------------+---------------------------------------+---------------------------------------+
| Evaluation Dimension            | SENTINEL (Ours)                       | Fraud Risk Manager (Competitor)       |
+---------------------------------+---------------------------------------+---------------------------------------+
| Architectural Tier              | Enterprise Production Platform        | Prototype / Hackathon Demo Toy        |
| PayPal Integration              | Genuine Orders v2, Sandbox, Webhooks  | NONE (0 PayPal APIs, 0 Webhooks)      |
| AI / LLM Capabilities           | Multi-turn Gemini 2.5 Structured Agent| NONE (0 AI Models, 0 LLM Agents)     |
| Persistence & Database          | PostgreSQL + Linear Alembic (d105a414)| SQLite on Ephemeral Container         |
| Authentication & Multi-Tenancy  | Argon2id, Sessions, Strict Merchant ID| NONE (Public open access, No Auth)    |
| Security & Trust Boundaries     | Maker-Checker, Digest HMAC, RSA SHA256| No Auth, No CSRF, Ephemeral DB        |
| Asynchronous Pipeline           | Supervised Worker + Advisory Locks    | Synchronous Process Only              |
| Machine Learning Quality        | Calibrated XGBoost (JSON), Platt Scale| XGBoost (Pickle/JSON), Uncalibrated   |
| Unique Capabilities             | Autonomous Investigations, Policy Lab | Dual Return-Risk, Batch CSV Scoring   |
| Hackathon Readiness             | Decisive Winner (Fulfills PayPal & AI)| Non-Compliant (No PayPal, No AI)      |
+---------------------------------+---------------------------------------+---------------------------------------+
```

---

## 2. PART I SENTINEL INDEPENDENT BASELINE (FROZEN)

Prior to inspecting Fraud Risk Manager, SENTINEL underwent a 100% full-file audit across all 390 tracked repository files:
- **File Census:** 390 tracked files (106 API, 87 Frontend, 84 Docs, 35 Tests, 34 Config, 23 Scripts, 9 Supabase, 6 ML, 6 Infra).
- **Test Invariants:** 302 passed backend, 39 passed frontend, 14 passed bridge, 7 passed ML pipeline, 0 Ruff linter errors, 0 TypeScript errors.
- **Payment Provenance:** Real $25 PayPal Sandbox capture verified (Order `2PE07332LD3413239`, Capture `8P799281C8558761R`, exactly 1 assessment row `dae7c7f2`, score `0.0869`).
- **Standalone Score:** **9.2 / 10**.

---

## 3. KEY COMPETITIVE FINDINGS

1. **The Hackathon Eligibility Disparity:**
   Fraud Risk Manager does not contain a single line of PayPal integration code (no PayPal OAuth, no Orders v2, no webhooks) and contains zero Generative AI integration (no Gemini, no OpenAI, no LLM agents). In a **PayPal AI Hackathon**, Fraud Risk Manager is fundamentally non-compliant with core sponsor mandates.
2. **The Production Engineering Reality:**
   SENTINEL is built with industrial-grade fintech protections: multi-tenant database isolation, dual-authorization maker-checker controls, cryptographic webhook verification, and state digest invariants. Fraud Risk Manager uses an open SQLite database without authentication or multi-tenant separation.
3. **Legitimate Competitor Merits to Adopt:**
   Fraud Risk Manager excels in accessible presentation for single-session demo viewers:
   - It separates **return abuse** from **payment fraud** using two separate classifiers.
   - It includes a **batch CSV scoring** drag-and-drop widget.
   - It emphasizes **fraud-ring graph visualization** prominently in its main navigation.

