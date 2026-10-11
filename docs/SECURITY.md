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

## Phase 4: investigations, evidence and approvals (implemented and tested)
- **Merchant isolation:** every investigation, evidence, packet and approval route loads the case
  through the principal's merchant first; ids from another merchant (or another case of the same
  merchant) return 404. Tested for each route family.
- **Agent scope:** read-only tools bound server-side to one authorised case; no tool accepts a
  merchant, case or transaction id; no mutation tools exist. Attempts to call unknown tools are
  logged as `denied`. Output is rejected if it cites records the run did not read, quotes text not
  in the evidence, mentions unknown identifiers or claims an action was taken. See
  `docs/AGENT_DESIGN.md`.
- **Prompt injection:** uploaded text and notes reach the model only inside tool results marked
  untrusted; instructions are constants. Tested with an injected PDF.
- **Uploads:** authenticated ADMIN/ANALYST + CSRF; PDF, PNG, JPEG only; declared type, extension
  and file signature must agree; 10 MB cap (read is bounded); PDFs with JavaScript, launch
  actions, embedded files, XFA or encryption are refused (a byte-level heuristic, not a full PDF
  sanitiser); text extraction only (pypdf), no rendering, no OCR; SHA-256 recorded; duplicate files
  per case refused. Acceptance never implies authenticity; everything is `MERCHANT_PROVIDED`.
- **Storage:** server-generated keys (`<merchant>/<kind>/<uuid>`) validated by regex and path
  containment; filenames are display-only. Local backend writes to a private directory
  (`var/storage`, 0600 files) outside any static path; `database` backend for hosts without a
  persistent disk. Files are served only by authorised routes with `Content-Disposition:
  attachment`, `Content-Security-Policy: default-src 'none'; sandbox`, `nosniff`, `no-store`.
- **Approvals:** server-built action snapshot with SHA-256, immutable in the database (trigger);
  decider must hold a required role, be in the merchant and not be the requester; one decision
  per request (row lock + unique constraint + trigger), tested with concurrent threads. Refund
  approvals record intent only: `action_executions.provider_called` is constrained to `false` and
  tests fail if any gateway `refund_capture` is invoked. The client never sends amounts.
- **Audit:** new events carry ids, hashes, sizes and enum values only. Filenames, descriptions,
  extracted text, justifications, comments and findings are kept out of `audit_events` (tested).
- **Secrets:** the AI key is a `SecretStr`, never returned by `/ai/status` or stored on runs;
  provider error bodies are not persisted.

Known gaps (tracked in `IMPLEMENTATION_STATUS.md`): rate limiter is per-process; no CSP header yet (set at the static host in Phase 6); no antivirus scanning of uploads; PDF active-content detection is heuristic; investigations run as
in-process background tasks (not a durable queue); security review pass scheduled for Phase 6.
