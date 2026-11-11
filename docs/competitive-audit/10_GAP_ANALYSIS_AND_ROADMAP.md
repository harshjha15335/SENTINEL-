# 10 — GAP ANALYSIS AND PRIORITIZED IMPROVEMENT ROADMAP

**Comparison:** SENTINEL vs Fraud Risk Manager  
**Auditor:** Fintech Product Manager & Principal Architect  

---

## 1. GAP ANALYSIS

### A. Competitor Capabilities SENTINEL Lacks (Features Worth Borrowing)
1. **Batch CSV Scoring Interface (High Priority for Demo):**
   - *Description:* FRM provides a drag-and-drop CSV upload where merchants upload historical orders and get instant risk scores.
   - *Benefit:* Allows hackathon judges to test custom transaction batches without opening PayPal Sandbox.
2. **Dedicated Return-Abuse Risk Classifier (Medium Priority):**
   - *Description:* Predicting wardrobing / return abuse independently of payment fraud.
   - *Benefit:* Expands the merchant value proposition beyond stolen credit cards.
3. **High-Visibility Fraud Ring Network Graph (Medium Priority):**
   - *Description:* FRM elevates network graph clustering to a top-level tab with rich node visualizations. SENTINEL has `/network`, but making it prominent in the demo script strengthens visual impact.

### B. SENTINEL Advantages (Capabilities FRM Completely Lacks)
1. **Genuine PayPal Sandbox Integration:** Orders v2 create, buyer redirect approval, $25 capture, experience context, cryptographic RSA webhook verification.
2. **Autonomous Multi-Turn Gemini Investigation Agent:** Scoped read-only tools, grounded evidence citations, structured findings, single-request budget caps.
3. **Industrial Security & Multi-Tenancy:** Argon2id, session tokens, CSRF defense, strict `merchant_id` ORM scoping, maker-checker dual approvals.
4. **Production Persistence & Asynchronous Queues:** Managed PostgreSQL, linear Alembic migrations (`d105a4143283`), background pipeline worker with advisory locks.
5. **Interactive Policy Lab:** Live threshold exploration with simulated flag rates vs merchant fraud savings.
6. **State Digest Verification:** Cryptographic HMAC state verification on refunds to prevent race conditions and duplicate payouts.

### C. Internal SENTINEL Weaknesses to Monitor
1. **Historical Webhook Discrepancy:** The exact caller that marked Supabase row `9881abb6` as `PROCESSED` without FastAPI delivery is unproven from logs alone.
2. **Hosted Automated Delivery:** Manual recovery proved reconciliation, but automatic webhook delivery on live cloud hosts remains pending hosted acceptance testing.

---

## 2. THREE-TIERED IMPROVEMENT ROADMAP

### PLAN A — MINIMUM VIABLE WINNING HACKATHON SUBMISSION (Next 2 Hours)
- **Action 1:** Complete cloud container deployment on Render using the synchronized `main` branch (`v2.0.0-rc1`).
- **Action 2:** Configure live staging environment secrets (`SENTINEL_DATABASE_URL`, `SENTINEL_PAYPAL_CLIENT_ID`, `SENTINEL_PAYPAL_CLIENT_SECRET`, `SENTINEL_SUPABASE_SERVICE_ROLE_KEY`, `SENTINEL_AI_API_KEY`).
- **Action 3:** Run `/api/v1/ready` readiness smoke-test to verify all workers report healthy heartbeats.
- **Action 4:** Record the 3-minute Devpost demo video showcasing:
  1. Live PayPal Sandbox checkout ($25 payment).
  2. Immediate calibrated risk scoring in Command Center.
  3. Case opening and autonomous Gemini multi-turn investigation in the Workbench.
  4. Two-person maker-checker approval.

### PLAN B — DECISIVELY CRUSH FRAUD RISK MANAGER (Next 24 Hours)
- **Feature 1:** Add a **Batch CSV Scoring** widget in `/transactions` allowing judges to drag-and-drop a sample CSV of 100 transactions and receive instant calibrated risk scores.
- **Feature 2:** Enhance the `/network` page with interactive node highlighting for shared cards, device IDs, and IP clusters.

### PLAN C — PRODUCTION-GRADE FINTECH PLATFORM (Post-Hackathon)
- Split worker processes into separate independent container deployments (separate API, Pipeline, and Bridge).
- Add support for PayPal Disputes v1 Webhook intake and automated dispute evidence submission via PayPal Dispute API.
- Introduce second classifier for return-abuse / friendly-fraud prediction.

