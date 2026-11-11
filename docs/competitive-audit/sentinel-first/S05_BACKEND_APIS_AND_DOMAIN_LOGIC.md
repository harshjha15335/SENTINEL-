# S05 — BACKEND APIS AND DOMAIN LOGIC AUDIT

**System:** SENTINEL FastAPI Backend (`apps/api/app`)  
**Framework:** FastAPI 0.143.0, Uvicorn 0.54.0, SQLAlchemy 2.1.4, Pydantic 2.14.0, Psycopg 3.3.6  
**Audit Coverage:** 100% of route definitions, controllers, schemas, and persistence services  

---

## 1. ENDPOINT REGISTRY & AUTHENTICATION MATRIX

| HTTP Method & Path | Controller / Route File | Role / Auth Dep | Service Layer Implementation | Persistence & Unit of Work | Test Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/auth/login` | `api/v1/auth.py` | Public + RateLimit | `AuthService.authenticate` (Argon2id) | Issues secure `session` cookie & CSRF token | `test_health_auth.py` |
| `POST /api/v1/auth/logout` | `api/v1/auth.py` | `get_current_user` | `AuthService.revoke_session` | Deletes session record from DB | `test_health_auth.py` |
| `GET /api/v1/auth/me` | `api/v1/auth.py` | `get_current_user` | `AuthService.get_principal` | Reads user role, email, merchant profile | `test_health_auth.py` |
| `POST /api/v1/checkout/orders` | `api/v1/checkout.py`| `get_current_user` | `PayPalGateway.create_order` | Persists Order record, sets experience_context | `test_checkout.py` |
| `POST /api/v1/checkout/orders/{id}/capture` | `api/v1/checkout.py`| `get_current_user` | `PayPalGateway.capture_order` | Idempotent capture, triggers synchronous scoring | `test_checkout.py` |
| `GET /api/v1/paypal/return` | `api/v1/paypal.py` | Public (Token-bound)| Validates order token & PayerID | Validates checkout URL redirect security | `test_checkout.py` |
| `POST /api/v1/webhooks/paypal`| `api/v1/webhooks.py`| Public (RSA Sig) | `WebhookVerifier` + `PaymentEventService` | Persists `PaymentEvent` (PROCESSED) & `RiskScoringJob` | `test_webhooks.py` |
| `GET /api/v1/cases` | `api/v1/cases.py` | `ANALYST`, `ADMIN` | `CaseService.list_cases` (Merchant-scoped) | Queries `Case` with status/priority filtering | `test_risk_cases.py` |
| `GET /api/v1/cases/{id}` | `api/v1/cases.py` | `ANALYST`, `ADMIN` | `CaseService.get_case_detail` | Eager loads transaction, evidence, assessment | `test_risk_cases.py` |
| `POST /api/v1/cases/{id}/resolve` | `api/v1/cases.py`| `ANALYST`, `ADMIN` | `CaseService.resolve_case` | Updates status (`APPROVED`/`BLOCKED`), logs audit | `test_risk_cases.py` |
| `POST /api/v1/cases/{id}/investigations` | `api/v1/investigations.py`| `ANALYST`, `ADMIN` | `InvestigationRunner.run` | Executes multi-turn Gemini investigation | `test_investigations.py` |
| `POST /api/v1/cases/{id}/evidence` | `api/v1/evidence.py` | `ANALYST`, `ADMIN` | `EvidenceService.upload` | Validates file header, MIME, stores in DB blob | `test_evidence_packets.py`|
| `GET /api/v1/cases/{id}/packet` | `api/v1/evidence.py` | `ANALYST`, `ADMIN` | `PacketService.generate_pdf` | Assembles ReportLab dispute packet with digest | `test_evidence_packets.py`|
| `POST /api/v1/approvals/{id}/approve` | `api/v1/approvals.py`| `ADMIN` only | `ApprovalService.approve` | Two-person maker-checker verification | `test_approvals.py` |
| `POST /api/v1/policy/simulate` | `api/v1/policy.py` | `ADMIN` only | `PolicyService.simulate` | Evaluates threshold shifts over historical data | `test_policy_lab.py` |
| `POST /api/v1/refunds/{id}/execute` | `api/v1/refunds.py` | `ADMIN` only | `RefundService.execute` | Checks snapshot digest, prevents duplicate refunds | `test_refunds.py` |
| `GET /api/v1/health` | `api/v1/health.py` | Public | Liveness check | Returns `{ "status": "ok" }` | `test_health_auth.py` |
| `GET /api/v1/ready` | `api/v1/health.py` | Public | Deep readiness check | Probes DB, Alembic schema version, worker heartbeats | `test_readiness_gate.py` |

---

## 2. BUSINESS LOGIC & DATA INTEGRITY CONTROLS

1. **Merchant Isolation (Multi-Tenant BOLA/IDOR Defense):**
   - Every single database query in `CaseService`, `TransactionService`, `EvidenceService`, and `PolicyService` includes an explicit filter: `WHERE merchant_id == principal.merchant_id`. Cross-tenant data leakage is structurally impossible.
2. **Maker-Checker Dual Authorization:**
   - In `apps/api/app/api/v1/approvals.py`, an administrator cannot approve their own high-risk actions. If `action.created_by_user_id == current_user.id`, the endpoint raises `HTTP 403 Forbidden ("Self-approval is forbidden by maker-checker policy")`.
3. **Refund Snapshot Digest Invariant:**
   - When executing a refund, the API validates the client-supplied `snapshot_digest` against `sha256(transaction_state)`. If the transaction has been altered, refunded, or disputed concurrently, the digest mismatch rejects execution with `HTTP 409 Conflict`.
4. **Idempotent Webhook Receipt Matching:**
   - Every webhook response returns an authoritative cryptographic receipt containing `receipt_id`, `event_id`, and `payload_sha256`. The upstream bridge will refuse to acknowledge without this exact receipt structure.

