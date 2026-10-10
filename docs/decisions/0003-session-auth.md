# 0003 · Server-side sessions with HttpOnly cookies and CSRF double-submit

Status: accepted (2026-10-10)

**Decision.** Email + Argon2id password login. A random session token is set as an HttpOnly,
SameSite=Lax cookie; only its SHA-256 digest is stored (`user_sessions`). A separate CSRF token is
returned and set as a readable SameSite=Strict cookie; every non-GET request must echo it in
`X-CSRF-Token`, compared in constant time against the stored digest. Roles (ADMIN, ANALYST,
VIEWER) are enforced by FastAPI dependencies; every query is scoped by the principal's merchant.

**Why not JWT/OAuth provider.** Revocation is immediate, nothing sensitive lives in JS-readable
storage, and no external identity provider account is needed for judges to run the project.

**Consequences.** Login rate limiting is in-process (single instance); swap for a shared store
before scaling horizontally.
