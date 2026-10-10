# Baseline Comparison

Benchmark: Aaryan Pawar's *Fraud Risk Manager* (github.com/aaryanpawar16/fraud-risk-manager),
built for a **Razorpay** hackathon. It is All Rights Reserved: SENTINEL contains none of its
source, assets, styling or component code, and nothing here was derived from reading its code.
Capabilities and limitations below come from the project brief's prior review; we could not
re-inspect the repository from this environment (GitHub access to it is not enabled).

Status vocabulary matches `IMPLEMENTATION_STATUS.md`.

| Capability | Benchmark (per brief) | SENTINEL implementation | Additional value | Status |
|---|---|---|---|---|
| Payment provider integration | No central PayPal integration (Razorpay context) | PayPal Orders v2 create/capture via a typed gateway; v6 JS SDK buttons; capture amount re-verified against server price | Real provider IDs, idempotency (`PayPal-Request-Id`), provenance on every record | Implemented and tested against HTTP mocks + fixture; **live sandbox run blocked on credentials** |
| Webhooks | Not described | Certificate-based signature verification, raw-body storage, idempotent intake, out-of-order-safe reconciliation, durable retry worker | Verified vs simulator events separated | Implemented and tested (signed test certs); not yet exercised with real PayPal deliveries |
| Authentication | No robust merchant auth | Argon2id + server sessions, CSRF, RBAC (ADMIN/ANALYST/VIEWER), merchant isolation, login rate limit, audit log | Tenant isolation tested | Implemented and tested |
| Storage | SQLite-centred | PostgreSQL 16 + Alembic migrations, constraints, indexes, timezone-aware timestamps, minor-unit money | Concurrency-safe capture via row locks | Implemented and tested |
| Fraud scoring | Present | Planned: Track A benchmark + Track B operational model, chronological splits, calibration | Leakage tests, thresholds chosen on validation only | Not started (Phase 3). UI shows "Not scored" rather than a placeholder |
| Chargeback/return-risk modelling | Present | Planned via refund/dispute history features | — | Not started |
| SHAP explanations | Present | Planned for tree models with provenance and limitations | Non-causal framing in UI | Not started |
| Review queues | Present | Planned: cases from risk/webhook events | Approval workflow with audit | Not started (Phase 2/4) |
| Network fraud patterns | Present | Planned: NetworkX graph with per-edge provenance | Every edge has a discoverable source | Not started (Phase 5) |
| Spike detection | Present | Planned as velocity/anomaly features | — | Not started |
| Evidence packets | Present (provenance concerns) | Planned: SHA-256 checksummed uploads, ReportLab packet with AI analysis labelled as analysis | Never claims delivery proof from an order confirmation | Not started (Phase 4) |
| Policy simulations | Present (threshold tuned on holdout) | Planned: validation-only selection, shadow mode, versioned policies | Correct data split | Not started (Phase 5) |
| Alerts | Present | Planned in Command Center | — | Not started |
| Frontend testing | Limited | Vitest + Testing Library (12 tests), Playwright desktop + mobile with axe WCAG 2.2 AA | Accessibility checked, not assumed | Implemented and tested |
| AI investigation agent | Not described | Planned: PydanticAI tool-calling with read-only, merchant-scoped tools | No payment mutation tools | Not started (Phase 4) |
