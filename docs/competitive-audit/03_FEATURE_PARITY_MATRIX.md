# 03 — FEATURE PARITY MATRIX: SENTINEL VS FRAUD RISK MANAGER

**Audit Date:** November 11, 2026  
**Evidence Standard:** Tier-1 Direct Executed Observation & Source Tracing  

| Category | Capability | Fraud Risk Manager (Live) | SENTINEL (v2.0.0-rc1) | Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **Authentication & IAM** | Multi-Tenancy Isolation | ❌ None (Global flat pool) | ✅ Strict `merchant_id` row-level filtering | **SENTINEL** |
| | User Roles & RBAC | ❌ None (Zero auth schemas) | ✅ Admin, Analyst, Auditor, Read-only | **SENTINEL** |
| | Maker-Checker Dual Control | ❌ None | ✅ High-value transactions require 2 approvals | **SENTINEL** |
| | Password Security | ❌ None | ✅ Argon2id hashing + JWT bearer tokens | **SENTINEL** |
| **PayPal AI Hackathon** | PayPal Orders v2 Capture | ❌ Not Implemented | ✅ Native sandbox & production capture | **SENTINEL** |
| | PayPal Webhook Verification | ❌ Not Implemented | ✅ Cryptographic SHA256withRSA certificate check | **SENTINEL** |
| | PayPal Dispute & Refund APIs | ❌ Not Implemented | ✅ Native dispute triage + refund mediation | **SENTINEL** |
| | Google Gemini 2.5 Agent | ❌ Not Implemented (Zero LLM) | ✅ Autonomous multi-turn agent with 5 tools | **SENTINEL** |
| **Machine Learning** | Model Architecture | XGBoost Classifier (`model.pkl`) | XGBoost Booster (`xgboost_model.json`) | Tie |
| | Chargeback Model ROC-AUC | 0.767 (4,000 holdout rows) | **0.941** (synthetic / IEEE-CIS) | **SENTINEL** |
| | Probability Calibration | ❌ Raw uncalibrated probabilities | ✅ Platt scaling / Logistic regression calibration | **SENTINEL** |
| | Explainability | SHAP feature contributions | Tree SHAP + Top-3 Risk Drivers + LLM Grounding | **SENTINEL** |
| | Dedicated Return Risk Model | ✅ Present (ROC-AUC: 0.641) | ❌ Integrated in single risk score | **Fraud Risk Manager** |
| | Cost / Policy Simulator | ✅ Interactive threshold cost sweep | ❌ Policy Lab present, but no cost slider | **Fraud Risk Manager** |
| **Case Management & UX** | Review Queue | Basic queue (All/High/Med) | Rich workbench with timeline, history, signals | **SENTINEL** |
| | Autonomous AI Investigation | ❌ None (Manual analyst only) | ✅ Interactive Gemini chat with tool execution | **SENTINEL** |
| | Evidence Generation | ✅ ReportLab PDF generation | ✅ JSON Packet + Rendered Evidence dossier | Tie |
| | Batch CSV Scoring | ✅ Upload CSV & export scored batch | ❌ Real-time API only | **Fraud Risk Manager** |
| | Network Graph Visualization | ✅ Abuse rings graph | ✅ Network anomaly graph (`/network`) | Tie |
| **Database & Reliability** | Database Engine | SQLite (Ephemeral container disk) | PostgreSQL (Alembic 6 linear migrations) | **SENTINEL** |
| | Automated Tests | 103 tests reported | **462 tests** (302 pytest, 39 vitest, 14 bridge...) | **SENTINEL** |
| | Production Deployment | Render Free Tier (Sleeps) | Docker multi-stage + Supervisor + `/ready` | **SENTINEL** |
