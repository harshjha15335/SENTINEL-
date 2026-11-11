# 02 — FRAUD RISK MANAGER LIVE RECONNAISSANCE & ARCHITECTURAL AUDIT

**Target:** Fraud Risk Manager  
**Public Frontend (Vercel):** `https://fraud-risk-manager.vercel.app/`  
**Public Backend (Render):** `https://fraud-risk-manager.onrender.com/`  
**Observation Date:** November 11, 2026  
**Auditor:** Multi-Perspective Panel (Architect, ML, FinTech PM, UI/UX, Security, QA, Judge)  
**Evidence Standard:** Tier-1 Direct Executed Observation & Live API Spec Forensics  

---

## 1. PUBLIC AVAILABILITY & OBSERVABILITY STATUS

- **Frontend (Vercel):** **VERIFIED LIVE (HTTP 200)**  
  Single-page application bundled with Vite, Tailwind CSS, Lucide icons, and React. Serves landing page at `/` and full risk console under `/app/*`.
- **Backend (Render):** **VERIFIED LIVE (HTTP 200 after cold-start)**  
  Initially unobservable due to free-tier spin-down (50s timeout). Upon warm-up, responded with `HTTP 200` to `/openapi.json` (23,553 bytes), `/metrics` (live JSON), `/review` (live cases), and `/fraud-spikes`.
- **UI Capture & Visual Verification:**  
  All 7 core application routes were directly loaded in Microsoft Edge via Playwright, verified against live DOM, and visually archived under `docs/competitive-audit/assets/`:
  1. Landing Page: `frm_01_landing_desktop.png` & `frm_mobile_375x812.png`
  2. Console Overview (`/app`): `frm_route_overview.png`
  3. Single Scoring (`/app/score`): `frm_route_score.png`
  4. Batch CSV Scoring (`/app/batch`): `frm_route_batch.png`
  5. Review Queue (`/app/review`): `frm_route_review.png`
  6. Abuse Rings Graph (`/app/graph`): `frm_route_graph.png`
  7. Fraud Spikes (`/app/spikes`): `frm_route_spikes.png`
  8. Chargeback Evidence (`/app/evidence`): `frm_route_evidence.png`

---

## 2. VERIFIED ENDPOINT REGISTRY (FROM LIVE OPENAPI 3.1.0 SPEC)

The live backend serves exactly **12 endpoints**:

| Endpoint Path | Method | OpenAPI Operation ID | Description / Implementation | SENTINEL Equivalent |
| :--- | :--- | :--- | :--- | :--- |
| `/score` | `POST` | `score_score_post` | Real XGBoost model (`ml/artifacts/model.pkl`) + SHAP factors | `POST /api/v1/checkout/orders/{id}/capture` |
| `/score/batch` | `POST` | `score_batch_upload_score_batch_post` | Multipart CSV upload scoring batch orders | Not implemented (SENTINEL is real-time checkout focused) |
| `/batch-files/{fn}`| `GET` | `download_batch_batch_files__filename__get` | Download scored batch CSV export | N/A |
| `/review` | `GET` | `get_review_queue_review_get` | Fetches active manual review queue from SQLite | `GET /api/v1/cases` |
| `/review/{id}` | `GET` | `get_review_case_review__order_id__get` | Fetches single order review details | `GET /api/v1/cases/{id}` |
| `/review/{id}` | `POST` | `resolve_review_case_review__order_id__post`| Analyst decision (approve/reject/refund) | `POST /api/v1/cases/{id}/decision` |
| `/review/resolved`| `GET` | `get_resolved_queue_review_resolved_get` | Fetches historically resolved cases | `GET /api/v1/cases?status=RESOLVED` |
| `/metrics` | `GET` | `get_metrics_metrics_get` | Model metrics, ROC-AUC, PR-AUC, cost sweep | `GET /api/v1/risk/model` |
| `/graph` | `GET` | `get_abuse_graph_graph_get` | NetworkX fraud-ring entity relationship graph | `GET /api/v1/network` |
| `/fraud-spikes` | `GET` | `get_fraud_spikes_fraud_spikes_get` | Velocity and temporal anomaly spike report | `GET /api/v1/monitoring` |
| `/evidence/{id}` | `GET` | `get_evidence_packet_evidence__order_id__get` | Auto-compiled evidence JSON packet | `GET /api/v1/cases/{id}/packet` |
| `/evidence-files/{id}.pdf` | `GET` | `download_evidence_pdf_evidence_files__order_id__pdf_get` | Download ReportLab generated PDF | `GET /api/v1/cases/{id}/evidence.pdf` |

---

## 3. LIVE MODEL TELEMETRY (FROM `/metrics`)

Live execution of `GET /metrics` against `https://fraud-risk-manager.onrender.com/metrics` revealed:
- **Holdout Dataset Size:** 4,000 rows
- **Holdout Positive Rate:** 11.3% fraud rate
- **Chargeback Model ROC-AUC:** `0.7668`
- **Chargeback Model PR-AUC (Average Precision):** `0.4526`
- **Cost Assumptions (INR):** False Positive Cost = ₹350; False Negative Cost = ₹4,500
- **Cost-Optimal Threshold:** `0.25`
  - Precision: `16.86%`
  - Recall: `84.51%`
  - F1-Score: `0.2811`
  - Confusion Matrix: TP = 382, FP = 1,884, FN = 70, TN = 1,664
  - Expected Cost: ₹9,74,400
- **Return-Risk Model ROC-AUC:** `0.6414` (secondary model trained specifically on `returned` label)
- **Automated Test Suite:** 103 tests reported in bundle

---

## 4. ARCHITECTURAL COMPARISON & VULNERABILITIES

### Critical Competitor Flaws
1. **Total Absence of Authentication & Multi-Tenancy:**
   - OpenAPI spec contains zero `securitySchemes` (no JWT, no Bearer, no API key).
   - Any public user hitting `/review/{order_id}` can approve, reject, or wipe cases without authentication.
   - All orders share a single global flat pool (no `merchant_id` isolation).
2. **Ephemeral SQLite Database:**
   - Uses SQLite on Render's ephemeral container disk. Every container restart or redeploy erases all manual review resolutions and case history.
3. **Zero PayPal Integration (Disqualifying for PayPal Track):**
   - No PayPal Orders v2 SDK, no webhook signature verification (`PAYPAL-AUTH-ALGO`, `PAYPAL-CERT-URL`), no PayPal dispute mediation.
   - UI form fields explicitly assume Indian domestic payment methods: `upi`, `netbanking`, `cod`, and values in `₹` (INR).
4. **Zero Generative AI or Agent Workflows (Disqualifying for AI Agent Track):**
   - The "AI" claim refers solely to standard XGBoost tabular trees.
   - No LLM orchestration, zero Google Gemini models, zero autonomous tool calling, zero multi-turn conversational agents.

### Notable Competitor Strengths
1. **Dual-Model Formulation:** Explicitly separates Chargeback risk from Return abuse risk (`roc_auc: 0.6414`), addressing friendly fraud and merchant return fraud.
2. **Policy / Cost Simulator:** Beautiful interactive threshold sweep slider dynamically calculating expected financial loss based on merchant cost assumptions.
3. **Batch CSV Upload:** Self-service merchant feature allowing batch historical file uploads and scored CSV exports.
