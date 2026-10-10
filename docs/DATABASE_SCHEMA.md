# Database Schema

Migration: `apps/api/alembic/versions/20261010_9918334b15aa_initial_schema.py` (round-trip tested).

```mermaid
erDiagram
  merchants ||--o{ users : employs
  merchants ||--o{ products : sells
  merchants ||--o{ transactions : owns
  users ||--o{ user_sessions : has
  products ||--o{ transactions : "priced from"
  transactions ||--o{ payment_events : "reconciled by"
  raw_payloads ||--o{ payment_events : "body of"
  merchants ||--o{ audit_events : scopes
```

| Table | Key columns | Constraints / notes |
|---|---|---|
| merchants | id, name, status, environment (SANDBOX/DEMO) | |
| users | merchant_id, email, password_hash (Argon2id), role, last_login_at | unique email |
| user_sessions | user_id, token_digest, csrf_digest, expires_at, revoked_at | only SHA-256 digests stored |
| products | merchant_id, sku, price_minor, currency | unique (merchant, sku); price > 0; ISO currency length |
| transactions | merchant_id, product_id, quantity, paypal_order_id, paypal_capture_id, amount_minor, currency, status, provider_status, payer_reference, create_idempotency_key, paypal_request_id, provider_summary (JSONB, redacted subset), failure_reason, data_origin, occurred_at | unique order id, capture id, (merchant, idempotency key); amount > 0; index (merchant, created_at) |
| payment_events | provider_event_id, provider_event_type, resource_id, payload_sha256, payload_reference → raw_payloads, transmission_id, verification_status, processing_status, delivery_count, attempts, data_origin, occurred_at, received_at, processed_at, error_reason | unique provider_event_id |
| raw_payloads | sha256, body (bytea) | restricted store; no API exposes it |
| audit_events | merchant_id, actor_id, actor_type, action, entity_type, entity_id, correlation_id, metadata (JSONB, redacted) | index (merchant, created_at) |

Money is always integer minor units + ISO-4217 code. All timestamps are `timestamptz`.
Buyer email and name from PayPal responses are not persisted; only `payer_id` as `payer_reference`.

## Planned tables (added with the phase that uses them)
risk_assessments, model_versions (Phase 3) · investigation_cases, investigation_runs,
evidence_artifacts, approvals, action_executions (Phase 2/4) · disputes, graph_entities,
graph_edges, policy_versions (Phase 5). Field lists follow the project brief §8.
