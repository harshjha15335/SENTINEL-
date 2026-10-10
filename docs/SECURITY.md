# Security

Implemented and tested:
- Argon2id password hashing; timing-equalised unknown-email path; generic login error.
- Server-side sessions (HttpOnly, SameSite=Lax cookie; token digest stored), immediate revocation on logout, 8-hour TTL.
- CSRF: double-submit token required on every non-GET authenticated request, constant-time compare.
- RBAC enforced in FastAPI dependencies (ADMIN/ANALYST/VIEWER); viewer cannot create orders; audit log admin-only.
- Merchant isolation: every query filters by the principal's `merchant_id`; cross-tenant read/capture tested to return 404.
- Login rate limiting (per IP + email sliding window; in-process).
- No PayPal secret ever reaches the browser; only the public client id is returned by `/paypal/status`.
- Sandbox-only base URL; no live mode or UI toggle.
- Strict request schemas (unknown fields rejected); SQLAlchemy parameterised queries; PayPal ids validated before use in URLs.
- CORS limited to configured origins with credentials; security headers (nosniff, frame deny, referrer policy).
- JSON logs with key-based redaction; correlation id on every response and error.
- Webhooks: certificate signature verification with PayPal-host allowlist, raw body size cap (256 KiB), idempotent storage, raw bodies isolated in `raw_payloads`.
- Buyer PII minimisation: email/name from PayPal not persisted.

Known gaps (tracked in `IMPLEMENTATION_STATUS.md`): rate limiter is per-process; no CSP header yet (set at the static host in Phase 6); upload validation arrives with evidence ingestion; security review pass scheduled for Phase 6.
