# 05 — BACKEND, SECURITY, AND SYSTEM RELIABILITY AUDIT

**Comparison:** SENTINEL Backend Architecture vs Fraud Risk Manager  
**Auditor:** Principal Software Architect & Application Security Engineer  

---

## 1. PERSISTENCE & DATA INTEGRITY COMPARISON

| Dimension | SENTINEL (Ours) | Fraud Risk Manager (Competitor) | Reliability Impact |
| :--- | :--- | :--- | :--- |
| **Database Engine** | PostgreSQL with strict relational constraints | SQLite file (`database.db`) | **SENTINEL wins decisively.** PostgreSQL supports concurrent writes, connection pools, and transactional isolation. |
| **Ephemeral Disk Safety**| Database-backed storage (`SENTINEL_STORAGE_BACKEND=database`)| Local disk SQLite file | **FRM loses data on restart.** Render free containers have ephemeral filesystems. When FRM redeploys, all data vanishes. |
| **Schema Migrations** | 6 Linear Alembic revisions (`d105a4143283` target) | Static SQLite tables | SENTINEL supports safe schema evolution without downtime or data corruption. |
| **Concurrency Control** | PostgreSQL advisory locks (`7682346`) & `FOR UPDATE SKIP LOCKED` | SQLite file-level lock | SQLite crashes with `database is locked` under concurrent web traffic and worker operations. |

---

## 2. SECURITY & ACCESS CONTROL DEFENSE IN DEPTH

1. **Authentication & Session Security:**
   - **SENTINEL:** Uses Argon2id password hashing, cryptographically random 32-byte session tokens stored in DB, delivered in `HttpOnly`, `SameSite=Lax` cookies, paired with double-submit CSRF headers.
   - **FRM:** Zero authentication. Every endpoint is completely public and unauthenticated.
2. **Multi-Tenant Scoping (BOLA / IDOR):**
   - **SENTINEL:** Every query contains an explicit `WHERE merchant_id == principal.merchant_id` filter. Cross-merchant data leaks are impossible.
   - **FRM:** Single global database with no tenant isolation.
3. **Maker-Checker Dual Authorization:**
   - **SENTINEL:** High-risk actions (e.g. manual approval of flagged accounts or refund overrides) require two separate administrators (`creator_id != approver_id`).
   - **FRM:** None.
4. **PayPal Webhook Cryptographic Verification:**
   - **SENTINEL:** Verifies authentic RSA SHA-256 signatures against PayPal cert URLs fetched exclusively over HTTPS from authorized PayPal hosts.
   - **FRM:** Zero webhook verification (no webhooks supported).

