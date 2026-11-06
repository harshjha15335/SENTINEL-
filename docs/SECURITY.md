# Security

## Latest next-phase implementation — 6 November 2026

The new [technical report](NEXT_PHASE_REPORT.md) supersedes older feature-status and environment observations below. Guarded refunds, dispute preparation, validation-only Policy Lab, scoped monitoring/network views and a refreshed judge scenario are now implemented locally. Actual hosting, genuine PayPal/AI and remote bridge access remain separately blocked/unverified. See [setup](NEXT_PHASE_SETUP.md), [runbook](NEXT_PHASE_RUNBOOK.md), [architecture](NEXT_PHASE_ARCHITECTURE.md) and [demo](NEXT_PHASE_DEMO.md). Earlier dated inventories remain historical.

## Session 8 operational status — 22 October 2026

The current recovered branch adds supervised Supabase HTTP ingestion, durable scoring, exact-schema readiness, an administrator operations page and a private read-only judge scenario. The receiver is public; the Python application is still workspace-local. Certificate-host reachability now works; sandbox OAuth authentication failed. Real PayPal payments remain deliberately untested, and the real-AI test remains credential-gated. See [SESSION_8_REPORT.md](SESSION_8_REPORT.md), [HOSTING_READINESS.md](HOSTING_READINESS.md) and [PROVIDER_VERIFICATION.md](PROVIDER_VERIFICATION.md) for current evidence. Older dated results below are historical, not current deployment claims.

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

Known gaps (tracked in `IMPLEMENTATION_STATUS.md`): rate limiter is per-process; no antivirus scanning of uploads; PDF active-content detection is heuristic; investigations run as
in-process background tasks (not a durable queue); security review pass scheduled for Phase 6.

## Session 8 controls and limits

`SENTINEL_HOSTED_DEPLOYMENT=true` rejects nonproduction environment, insecure cookies, local evidence storage, disabled worker readiness and non-HTTPS CORS origins. Empty CORS is appropriate for same-origin hosting. Hosted supervisor startup rejects wildcard proxy trust; supply actual trusted addresses after inspecting the chosen host. These guards do not themselves provision HTTPS or shared rate limiting.

Operations requires ADMIN. Event, job, investigation and blob counts are merchant-scoped and origin-separated. Global inbox counts are available only to the merchant explicitly configured in `SENTINEL_OPERATIONS_INBOX_MERCHANT_ID`; the default exposes none. Snapshot age and stale heartbeats are visible. Responses are no-store and contain no raw receipt bodies or evidence text.

The judge account is a VIEWER in an isolated DEMO merchant. A trusted CLI creates synthetic material through existing domain services. Its internal curator password is randomly generated and discarded. Judge password comes from `SENTINEL_JUDGE_PASSWORD`, never a public route or source constant; repeat provisioning does not rotate it or overwrite unrelated merchant data. The prepared attachment explicitly says it is a demo document and remains unverified.

Dependency vulnerability scanning, a shared login limiter, antivirus/OCR and a durable investigation task queue remain limitations. Investigation runs still execute in-process with stale-run recovery; durable payment scoring does not imply durable AI execution.
