# SENTINEL — PAYPAL AI HACKATHON DEVPOST SUBMISSION PACKAGE

**Project Name:** SENTINEL  
**Tagline:** Autonomous AI Fraud Defense & Investigation Platform Powered by PayPal Orders v2 and Google Gemini 2.5  
**Hackathon:** PayPal AI Hackathon  
**Release Tag:** `v2.0.0-rc1` (Commit `3072f18`)  
**Repository:** [https://github.com/harshjha15335/SENTINEL-](https://github.com/harshjha15335/SENTINEL-)  

---

## 1. ELEVATOR PITCH & PROJECT OVERVIEW

### Tagline
*Autonomous AI Fraud Defense & Investigation Platform Powered by PayPal Orders v2 and Google Gemini 2.5.*

### One-Sentence Description
SENTINEL protects PayPal merchants from payment fraud, chargebacks, and friendly-fraud abuse by combining real-time calibrated XGBoost risk scoring with an autonomous multi-turn Google Gemini 2.5 investigation agent that synthesizes evidence, enforces two-person maker-checker approvals, and generates cryptographic dispute packets.

---

## 2. DEVPOST SUBMISSION FORM CONTENT

### Inspiration
Every year, digital merchants lose tens of billions of dollars to payment fraud, card-testing attacks, and chargeback abuse. When a suspicious transaction occurs, fraud analysts typically endure a fragmented, manual nightmare: cross-referencing buyer histories, inspecting device profiles, digging through IP logs, manually drafting dispute packets, and wrestling with uncalibrated "black-box" risk scores. 

We asked ourselves: **What if PayPal payment trust could be fully autonomous, scientifically calibrated, and radically transparent?** What if an AI agent didn't just flag a transaction, but conducted a complete, grounded forensic investigation—inspecting historical velocity, checking fraud rings, gathering evidence, and drafting dispute packets under strict human-in-the-loop governance? 

That vision became **SENTINEL**.

---

### What SENTINEL Does
SENTINEL is an end-to-end fraud intelligence and automated investigation platform designed specifically for the PayPal merchant ecosystem:

1. **Seamless PayPal Orders v2 Sandbox Integration:**
   Embeds official PayPal buttons into an interactive checkout experience, executing real-time order creation, buyer approval redirection, and idempotent payment capture.
2. **Scientifically Calibrated Real-Time Risk Scoring:**
   Scores payments instantaneously using an operational XGBoost model (native JSON booster, zero pickle vulnerability) calibrated via Platt sigmoid scaling. Scores reflect genuine empirical fraud probabilities, categorizing transactions into `LOW`, `MEDIUM`, or `HIGH` risk bands based on cost-optimized threshold boundaries ($4 review cost vs $20 chargeback fee).
3. **Autonomous Multi-Turn Gemini 2.5 Investigation Agent:**
   When high-risk transactions enter the Review Queue, an autonomous Gemini 2.5 agent conducts an interactive investigation. Using 5 scoped read-only tools, the agent queries customer tenure, transaction velocity, device profiles, and entity relationship graphs. It synthesizes grounded findings with clickable citations to factual database records—eliminating LLM hallucinations.
4. **Investigation Workbench & Evidence Management:**
   Analysts can upload evidence documents (invoices, shipping receipts), inspect entity relationships in the Network Explorer, and dynamically simulate threshold trade-offs in the Policy Lab.
5. **Two-Person Maker-Checker Dual Approvals:**
   High-risk actions (e.g. manual approval of flagged accounts or refund execution) require dual authorization (`creator_id != approver_id`), preventing rogue employee actions or unilateral mistakes.
6. **One-Click Cryptographic Dispute Packets:**
   Assembles comprehensive ReportLab PDF dispute defense packets complete with SHA-256 state digests, payment timelines, and attached evidence for instant submission to PayPal Resolution Center.

---

### How We Built It
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, TanStack React Query, Radix UI, and AG Grid virtualized tables. Built with an enterprise dark fintech terminal aesthetic and tested with `@axe-core` for accessibility.
- **Backend & APIs:** FastAPI, Uvicorn, SQLAlchemy 2.0 ORM, and Pydantic v2 settings. Single-origin container architecture eliminates production CORS complexity.
- **Machine Learning:** XGBoost (CPU), scikit-learn, and NumPy. Evaluated on a chronological 60/20/20 holdout split across 9,051 transactions (4.52% base rate), achieving an ROC-AUC of `0.8413` and PR-AUC of `0.3485` within an 8% operational review capacity budget.
- **Generative AI Agent:** Google Gemini 2.5 (`gemini-2.5-flash` / `gemini-3.1-flash-lite`) via `google-genai` and `pydantic-ai-slim`, hardened with single-request budget caps, modality-conflict stripping, and `httpx2` resilient decompression.
- **Database & Persistence:** Production PostgreSQL with 6 linear Alembic migrations (`d105a4143283` target) and startup schema verification gates.
- **PayPal & Webhook Infrastructure:** PayPal Orders v2 REST APIs with RSA SHA-256 certificate verification and Supabase PostgreSQL durable inbox with PostgreSQL advisory locks (`7682346`) and loopback connection pooling.

---

### Challenges We Overcame
- **The PayPal Sandbox Experience Context:** Diagnosing and correcting PayPal Orders v2 buyer approval return flows to ensure seamless local loopback redirects (`/api/v1/paypal/return`) without invalid external URLs.
- **Gemini Structured Output Modality Contradiction:** Resolving Google Gemini HTTP 400 errors by stripping conflicting `responseModalities` when strict tool calling schemas are active.
- **Loopback Webhook Resilience:** Designing a durable receipt matching invariant in the Supabase-to-FastAPI bridge worker so that webhooks are only acknowledged (`sentinel_finish_webhook`) when FastAPI confirms cryptographic payload and event matches.
- **Dual-Path Scoring Idempotency:** Guaranteeing that payments scored synchronously during capture are never redundantly re-scored when asynchronous webhooks arrive, preserving exactly 1 `RiskAssessment` row per transaction.

---

### Accomplishments We're Proud Of
- **Authentic PayPal Payment Execution:** Successfully captured real $25 Sandbox order `2PE07332LD3413239` (Capture `8P799281C8558761R`) with 100% cryptographic webhook reconciliation.
- **Zero Pickles in Production ML:** 100% safe, fast JSON model serialization with Platt sigmoid probability calibration.
- **Exhaustive Automated Verification:** 302 backend pytest tests passed, 39 frontend unit tests passed, 14 bridge invariant tests passed, and 7 ML pipeline tests passed (100% green).
- **Strict Multi-Tenant Security:** Every ORM query enforces `WHERE merchant_id == principal.merchant_id`, preventing any cross-merchant data leakage.

---

### What We Learned
We learned that the hardest part of building autonomous AI for fintech isn't getting an LLM to generate text—it's **grounding and bounding the agent**. By giving Gemini strictly typed, read-only tools scoped to the active tenant and capping its execution budget, we transformed a potentially hallucinating chatbot into a deterministic, reliable fraud investigator that human analysts can trust.

---

### What's Next for SENTINEL
1. **Live Dispute API Integration:** Automating two-way sync with the PayPal Disputes v1 API to submit generated ReportLab evidence packets directly into PayPal Resolution Center.
2. **Dedicated Return-Abuse Classifier:** Training a second model predicting friendly fraud / wardrobing abuse independently of stolen card fraud.
3. **Batch CSV Drag-and-Drop Scoring:** Providing high-volume merchants with instant bulk evaluation of historical transaction batches.

---

## 3. SCENE-BY-SCENE 3-MINUTE VIDEO SCRIPT

**Total Duration:** 2 minutes 58 seconds  
**Visual Mode:** High-resolution screen recording of the live SENTINEL V2 application.

```
+-----------------------------------------------------------------------------------------------------------------------+
| TIME        | ONSCREEN ACTION                                    | SPOKEN SCRIPT (VOICEOVER)                          |
+-------------+----------------------------------------------------+----------------------------------------------------+
| 0:00 - 0:25 | Camera opens on Command Center (/).               | "Online merchants face a relentless dilemma:       |
|             | Hover over KPI cards: $1.2M volume, flag rate,    | fraud costs billions, but manual reviews waste     |
|             | and transaction feed showing origin badges.        | hours. Welcome to SENTINEL—an autonomous AI fraud  |
|             |                                                    | defense platform built for PayPal and Gemini."     |
+-------------+----------------------------------------------------+----------------------------------------------------+
| 0:25 - 0:55 | Navigate to /checkout.                             | "Let's test it live. Here's our PayPal Sandbox     |
|             | Click the golden PayPal button.                    | checkout. We click Pay with PayPal, approve the    |
|             | Sandbox modal opens -> Buyer clicks "Pay Now".     | $25 transaction, and PayPal captures the payment.  |
|             | Redirects to /transactions with status: CAPTURED.  | Instantly, SENTINEL's calibrated XGBoost model     |
|             | Order & Capture IDs displayed with score 0.0869.   | scores the transaction with zero latency."         |
+-------------+----------------------------------------------------+----------------------------------------------------+
| 0:55 - 1:40 | Navigate to /cases (Review Queue).                | "Let's inspect our Review Queue. Case #412 was     |
|             | Click Case #412 -> Investigation Workbench opens.  | flagged for review. Instead of hunting through logs|
|             | Click "Run AI Investigation".                     | we launch our autonomous Gemini 2.5 agent. Watch   |
|             | Gemini tool calls execute in real time.            | as Gemini queries transaction velocity, checks     |
|             | Structured findings load with cited evidence.      | device fingerprints, and inspects the network      |
|             |                                                    | graph—generating a cited, hallucination-free report|
+-------------+----------------------------------------------------+----------------------------------------------------+
| 1:40 - 2:15 | Scroll to EvidencePanel -> Upload invoice PDF.     | "We attach an invoice to the case file and click   |
|             | Click "Generate Dispute Packet" -> PDF downloads.  | 'Generate Evidence Packet'. SENTINEL produces an   |
|             | Open ReportLab PDF showing timeline & SHA256 digest| official ReportLab dispute defense packet complete |
|             |                                                    | with cryptographic SHA-256 digests for PayPal."    |
+-------------+----------------------------------------------------+----------------------------------------------------+
| 2:15 - 2:40 | Navigate to /approvals.                            | "For security, high-risk recovery actions require  |
|             | Show Maker-Checker dual authorization.             | maker-checker dual approval. An admin cannot       |
|             | Admin signs in and approves the prepared refund.   | approve their own actions. Another admin reviews   |
|             | Success toast appears; audit log updated.          | the evidence and authorizes the refund safely."    |
+-------------+----------------------------------------------------+----------------------------------------------------+
| 2:40 - 2:58 | Quick glimpse of /policy (Policy Lab slider)       | "Finally, our Policy Lab lets merchants simulate   |
|             | and /network (fraud ring graph).                   | threshold trade-offs in real time. Calibrated ML,  |
|             | Close on SENTINEL logo & GitHub repository URL.    | autonomous Gemini agents, and real PayPal trust.   |
|             |                                                    | This is SENTINEL. Thank you!"                      |
+-------------+----------------------------------------------------+----------------------------------------------------+
```

---

## 4. JUDGE DEMO WALKTHROUGH & TEST CREDENTIALS

To enable hackathon judges to evaluate the platform immediately:

### Hosted Demo URL
- **Application URL:** `https://sentinel-demo.onrender.com` *(or local checkout on `http://127.0.0.1:8000`)*
- **API Documentation:** `/docs` (Interactive OpenAPI Swagger UI)
- **Health & Readiness Check:** `/api/v1/ready`

### Demo Credentials (Role-Based Access Control)
- **Administrator Account (Full Controls & Policy Lab):**
  * **Email:** `admin@sentinel.internal`
  * **Password:** *(Configured via `SENTINEL_SEED_ADMIN_PASSWORD` or demo seed)*
  * **Permissions:** Case resolution, dual-approvals, refund execution, Policy Lab tuning, worker observability.
- **Fraud Analyst Account (Investigation Workbench):**
  * **Email:** `analyst@sentinel.internal`
  * **Password:** *(Configured via `SENTINEL_SEED_ANALYST_PASSWORD`)*
  * **Permissions:** Review queue, Gemini investigation runner, evidence upload, packet assembly.
- **Read-Only Auditor Account:**
  * **Email:** `viewer@sentinel.internal`
  * **Password:** *(Configured via `SENTINEL_SEED_VIEWER_PASSWORD`)*
  * **Permissions:** Read-only inspection of transactions, monitoring drift charts, and model statistics.

