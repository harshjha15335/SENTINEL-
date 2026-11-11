# S09 — DATABASE SCHEMA, SECURITY, AND PRIVACY AUDIT

**System:** SENTINEL Data & Security Architecture  
**Database Engines:** PostgreSQL (Application DB + Supabase Inbox)  
**Security Scope:** Authentication, Authorization, CSRF, Multi-Tenant Isolation, Cryptographic Verification  

---

## 1. MIGRATION CHAIN & PERSISTENCE ORDER

```
Alembic Migrations (Application PostgreSQL):
  [1] 20261010_9918334b15aa_initial_schema.py
      - Core tables: merchants, users, sessions, transactions, orders
  [2] 20261010_67fa573a3cac_risk_assessments_and_cases.py
      - Tables: risk_assessments, cases, case_assignments
  [3] 20261011_f3742645a803_investigations_evidence_approvals.py
      - Tables: investigation_runs, evidence_items, approval_requests
  [4] 20261022_22ad61c52593_durable_webhook_scoring_jobs.py
      - Tables: payment_events, risk_scoring_jobs
  [5] 20261022_8ab7245e13c0_worker_observability.py
      - Tables: worker_health
  [6] 20261106_d105a4143283_refund_dispute_shadow_policy_workflows.py
      - Target Migration: d105a4143283
      - Tables: refunds, disputes, policy_simulations, shadow_decisions

Supabase SQL Migrations (Inbox PostgreSQL):
  [1] 202610200001_webhook_inbox.sql
      - Table: sentinel_webhook_inbox
  [2] 202610220002_bridge_lifecycle.sql
      - Stored Procedures: sentinel_claim_webhooks (FOR UPDATE SKIP LOCKED), sentinel_finish_webhook
```

---

## 2. SECURITY CONTROLS & THREAT MODEL AUDIT

| Security Dimension | Implementation Mechanism | Verified Status | Evidence |
| :--- | :--- | :--- | :--- |
| **Password Hashing** | Argon2id via `argon2-cffi` | **VERIFIED** | `apps/api/app/core/security.py` |
| **Session Management** | Cryptographically random session tokens (32 bytes) | **VERIFIED** | Stored in DB, delivered in `HttpOnly`, `SameSite=Lax` cookies |
| **CSRF Defense** | Double-submit CSRF cookie paired with `X-CSRF-Token` header | **VERIFIED** | Validated on all mutating endpoints (`POST`, `PUT`, `DELETE`) |
| **Multi-Tenant Isolation** | Scoped queries: `WHERE merchant_id == principal.merchant_id` | **VERIFIED** | Enforced across all ORM queries; no BOLA/IDOR possible |
| **Maker-Checker Dual Auth** | Rejection of self-approval: `creator_id != approver_id` | **VERIFIED** | `apps/api/app/api/v1/approvals.py` |
| **Refund Digest Protection**| Validates `sha256(transaction_state)` before executing refund | **VERIFIED** | Rejects concurrent state alterations (`HTTP 409`) |
| **Webhook RSA Verification**| Cryptographic verification against official PayPal cert URLs | **VERIFIED** | Restricts cert downloads to `api.sandbox.paypal.com` / `api.paypal.com` |
| **Secret Sanitization** | Pydantic `SecretStr` for client secrets & API keys | **VERIFIED** | Excluded from `repr()`, logs, and error responses |
| **SQL Injection Defense** | Parameterized queries via SQLAlchemy Core & ORM | **VERIFIED** | Zero raw string interpolation queries |
| **XSS Defense** | Strict React component tree rendering without `innerHTML` | **VERIFIED** | Zero unsafe DOM insertions |

