# S03 — ARCHITECTURE AND DATAFLOWS (VERIFIED)

**System:** SENTINEL Fraud Intelligence Platform  
**Audit Scope:** End-to-End Architectural Reconstruction from First-Party Source Code  

---

## 1. COMPONENT ARCHITECTURE & TOPOLOGY

```mermaid
flowchart TD
    subgraph Client ["Client Tier (Browser)"]
        SPA["SENTINEL V2 Web App\n(React 19 + Vite + Tailwind CSS)\napps/web/src"]
    end

    subgraph Host ["Unified Container Host (Single Origin :8000/:8040)"]
        SUPERVISOR["Worker Supervisor\n(app.workers.supervisor)\nGraceful shutdown & restart budgets"]
        
        subgraph APITier ["FastAPI Application (app.main:app)"]
            ROUTER["API Router (/api/v1/*)\nAuth, Checkout, Webhooks, Cases, Policy"]
            STATIC["Static File Server (/*)\nMounts apps/web/dist"]
        end

        subgraph Workers ["Supervised Background Workers"]
            PIPE_WORKER["Pipeline Worker (app.workers.pipeline)\nAdvisory Lock: 7682346\nScoring Job Consumer"]
            BRIDGE_WORKER["Supabase Bridge Worker\n(app.workers.supabase_inbox)\nRPC Poll & Loopback Forwarder"]
        end
    end

    subgraph DataTier ["Persistence Tier"]
        APP_DB[(Application PostgreSQL DB\nAlembic Migrations -> d105a4143283)]
        SUPA_DB[(Supabase PostgreSQL DB\nsentinel_webhook_inbox)]
    end

    subgraph External ["External Provider Integrations"]
        PAYPAL["PayPal REST API (Sandbox)\nOrders v2 & Experience Context"]
        GEMINI["Google Gemini 2.5 API\n(Structured Tools & Multi-turn)"]
        SUPA_EDGE["Supabase Edge Function\n(paypal-webhook receiver)"]
    end

    SPA -->|REST + Session Cookie| ROUTER
    SPA -->|Vite Static Assets| STATIC
    SUPERVISOR -.->|Spawns & Monitors| ROUTER
    SUPERVISOR -.->|Spawns & Monitors| PIPE_WORKER
    SUPERVISOR -.->|Spawns & Monitors| BRIDGE_WORKER

    ROUTER -->|SQLAlchemy Unit of Work| APP_DB
    PIPE_WORKER -->|Consumes Jobs & Updates Assessments| APP_DB
    BRIDGE_WORKER -->|RPC sentinel_claim_webhooks| SUPA_DB
    BRIDGE_WORKER -->|POST /api/v1/webhooks/paypal| ROUTER
    BRIDGE_WORKER -->|RPC sentinel_finish_webhook| SUPA_DB

    ROUTER -->|Orders v2 POST/GET/Capture| PAYPAL
    ROUTER -->|Pydantic-AI Runner| GEMINI
    PAYPAL -->|Signed Webhook Delivery| SUPA_EDGE
    SUPA_EDGE -->|INSERT INTO sentinel_webhook_inbox| SUPA_DB
```

---

## 2. DUAL-PATH RISK SCORING DATAFLOW & IDEMPOTENCY

SENTINEL implements two parallel ingestion paths for risk assessment:

```mermaid
sequenceDiagram
    autonumber
    actor Buyer as Sandbox Buyer
    participant PayPal as PayPal Orders v2
    participant API as FastAPI (:8040)
    participant DB as App PostgreSQL
    participant Supa as Supabase Edge / Inbox
    participant Bridge as Bridge Worker
    participant Pipe as Pipeline Worker
    participant XGB as XGBoost Model

    Note over Buyer, PayPal: Path A: Synchronous Capture & Immediate Scoring
    Buyer->>PayPal: Approves Order (experience_context return_url)
    Buyer->>API: Redirected to /api/v1/paypal/return
    API->>PayPal: POST /v2/checkout/orders/{id}/capture
    PayPal-->>API: 201 Created (Capture ID: 8P799281C8558761R)
    API->>XGB: Synchronous score_after_capture()
    XGB-->>API: Risk Score: 0.0869, Band: MEDIUM, Policy: REVIEW
    API->>DB: INSERT RiskAssessment (dae7c7f2) [Trigger: capture]
    API->>DB: UPDATE Transaction (b970504f) -> CAPTURED
    API-->>Buyer: Checkout Success Response

    Note over PayPal, Supa: Path B: Asynchronous Webhook Delivery
    PayPal->>Supa: Webhook: PAYMENT.CAPTURE.COMPLETED (WH-8PS64288...)
    Supa->>Supa: INSERT sentinel_webhook_inbox (status: PENDING)
    Bridge->>Supa: RPC sentinel_claim_webhooks() [FOR UPDATE SKIP LOCKED]
    Supa-->>Bridge: Claimed Row (9881abb6)
    Bridge->>API: POST /api/v1/webhooks/paypal (with authentic headers)
    API->>DB: INSERT PaymentEvent (65d36059) [Status: PROCESSED]
    API->>DB: INSERT RiskScoringJob (b27c85dc) [Status: PENDING]
    API-->>Bridge: HTTP 200 (receipt_id: PAYMENT.CAPTURE.COMPLETED:8P799...)
    Bridge->>Supa: RPC sentinel_finish_webhook(9881abb6, 'PROCESSED')

    Note over Pipe, DB: Deduplication & Re-use Invariant
    Pipe->>DB: Claim RiskScoringJob (b27c85dc)
    Pipe->>DB: Query RiskAssessmentService.latest_for(txn_id)
    DB-->>Pipe: Existing Assessment (dae7c7f2) Found!
    Pipe->>DB: UPDATE RiskScoringJob (b27c85dc) -> COMPLETED [assessment_id = dae7c7f2]
    Note over Pipe, DB: Exactly 1 RiskAssessment row exists. Zero duplicate scoring.
```

---

## 3. GEMINI MULTI-TURN INVESTIGATION WORKFLOW

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Fraud Analyst
    participant UI as Investigation Workbench
    participant API as FastAPI Investigation Router
    participant Runner as Investigation Runner
    participant Provider as Gemini Provider (httpx2)
    participant Model as Google Gemini 2.5
    participant DB as App PostgreSQL

    Analyst->>UI: Clicks "Run Investigation" on Case
    UI->>API: POST /api/v1/cases/{id}/investigations
    API->>DB: Create InvestigationRun (status: RUNNING)
    API->>Runner: Execute Multi-turn Investigation
    
    loop Tool Loop (Max 3 turns, strict single-request transport cap)
        Runner->>Provider: Build Prompt + Structured Tool Definitions
        Provider->>Model: POST /v1beta/models/gemini-2.5:generateContent
        Model-->>Provider: tool_calls (e.g. get_transaction_history, inspect_device)
        Provider-->>Runner: Dispatched Tool Call
        Runner->>DB: Read-only query scoped to merchant_id
        DB-->>Runner: Factual Entity Records
        Runner->>Provider: Return tool_result JSON
    end

    Model-->>Provider: Structured Finding (confidence, reasoning, risk_signals)
    Provider-->>Runner: Verified Schema Output
    Runner->>DB: UPDATE InvestigationRun -> COMPLETED
    Runner->>DB: Persist Findings & Citations
    API-->>UI: Investigation Complete (Deterministic Summary Displayed)
```

---

## 4. SUBSYSTEM STATUS CLASSIFICATION MATRIX

| Subsystem | Implemented Entrypoint | Verified Status | Evidence |
| :--- | :--- | :--- | :--- |
| **Orders v2 Sandbox Gateway** | `apps/api/app/services/paypal/sandbox.py` | **VERIFIED WORKING** | Real $25 Order `2PE07332LD3413239` captured |
| **Webhook Signature Verifier** | `apps/api/app/services/paypal/verifier.py` | **VERIFIED WORKING** | Tested with authentic PayPal RSA signatures |
| **Supabase Durable Inbox** | `supabase/functions/paypal-webhook/` | **VERIFIED WORKING** | PostgREST RPC, claim locks verified |
| **Inbox Bridge Worker** | `apps/api/app/workers/supabase_inbox.py` | **VERIFIED WORKING** | 14/14 unit & invariant tests passed |
| **XGBoost Inference Engine** | `apps/api/app/services/risk/evaluator.py` | **VERIFIED WORKING** | Evaluated transaction `b970504f`, score `0.0869` |
| **Dual-Path Scoring Idempotency**| `apps/api/app/services/scoring_jobs.py` | **VERIFIED WORKING** | Exactly 1 assessment row, 0 duplicates |
| **Investigation Workbench** | `apps/web/src/features/investigation/` | **VERIFIED WORKING** | Full multi-turn investigation and UI panels |
| **Two-Person Maker-Checker** | `apps/api/app/api/v1/approvals.py` | **VERIFIED WORKING** | Dual-authorization workflow verified |
| **Automated Cloud Deploy** | `render.yaml` (`autoDeploy: true`) | **IMPLEMENTED, UNVERIFIED** | Local contract passed, live host pending |

