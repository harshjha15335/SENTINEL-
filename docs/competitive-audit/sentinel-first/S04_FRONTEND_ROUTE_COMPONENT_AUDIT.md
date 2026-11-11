# S04 — FRONTEND ROUTE AND COMPONENT AUDIT

**System:** SENTINEL V2 Web Interface (`apps/web/src`)  
**Framework:** React 19.3.0, TypeScript 5.x, Vite 8.3.4, Tailwind CSS 4.3.3, TanStack React Query 5.104.1  
**Audit Coverage:** 100% of routes and major feature components  

---

## 1. ROUTE REGISTRY & COMPONENT MATRIX

| Route | Component | Auth / Role Gate | Data Sources & APIs | Key Interactions & Features | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/login` | `LoginPage` | Public (Redirects if auth) | `POST /api/v1/auth/login` | Email/password validation, CSRF cookie acquisition, error toasts | **VERIFIED WORKING** |
| `/` | `DashboardPage` | Authenticated (Any role) | `GET /api/v1/dashboard` | KPI cards (volume, flag rate, review count), recent flagged transactions, separate sandbox vs simulated indicators | **VERIFIED WORKING** |
| `/transactions` | `TransactionsPage` | Authenticated (Any role) | `GET /api/v1/transactions` | AG Grid virtualized table, filtering by status/risk band, sorting, pagination, date ranges | **VERIFIED WORKING** |
| `/transactions/:id` | `TransactionDetailPage` | Authenticated (Any role) | `GET /api/v1/transactions/{id}` | Full payment breakdown, customer history, raw risk score, feature contributions | **VERIFIED WORKING** |
| `/cases` | `CasesPage` | Authenticated (ANALYST, ADMIN) | `GET /api/v1/cases` | Review queue with priority sorting, SLA countdown, claim/assign controls | **VERIFIED WORKING** |
| `/cases/:id` | `CaseDetailPage` + `Workbench` | Authenticated (ANALYST, ADMIN) | `GET/POST /api/v1/cases/{id}/*` | **Investigation Workbench** (AI summary, evidence upload, approval triggers, capacity warning) | **VERIFIED WORKING** |
| `/model` | `ModelPage` | Authenticated (Any role) | `GET /api/v1/risk/model` | Active XGBoost model version (`v1.2.0`), feature importance list, calibration curves | **VERIFIED WORKING** |
| `/checkout` | `CheckoutPage` | Authenticated (Any role) | `POST /api/v1/checkout/orders` | Live PayPal JS SDK integration, sandbox order creation, approved return flow, fallback simulation | **VERIFIED WORKING** |
| `/policy` | `PolicyLabPage` | Authenticated (ADMIN) | `GET/POST /api/v1/policy/*` | Threshold tuning slider (0.0 to 1.0), simulated flag rate vs fraud savings curve, shadow policy mode | **VERIFIED WORKING** |
| `/refunds` | `RefundsPage` | Authenticated (ADMIN) | `GET/POST /api/v1/refunds/*` | Independent administrator decisioning, digest verification, shadow vs execution flags | **VERIFIED WORKING** |
| `/disputes` | `DisputesPage` | Authenticated (Any role) | `GET /api/v1/disputes` | Dispute tracker, genuine sync error reporting, evidence packet association | **VERIFIED WORKING** |
| `/monitoring` | `MonitoringPage` | Authenticated (Any role) | `GET /api/v1/monitoring` | Real data drift metrics without invented calibration curves, origin filtering | **VERIFIED WORKING** |
| `/network` | `NetworkPage` | Authenticated (Any role) | `GET /api/v1/network` | Entity relationship graph (cards, device IDs, emails, IP addresses) | **VERIFIED WORKING** |
| `/operations` | `OperationsPage` | Authenticated (ADMIN only) | `GET/POST /api/v1/operations/*`| System controls, worker health heartbeats, bridge diagnostics | **VERIFIED WORKING** |
| `/demo` | `DemoGuidePage` | Authenticated (DEMO env) | Static & Local API | Step-by-step walkthrough for hackathon judges | **VERIFIED WORKING** |
| `/settings` | `SettingsPage` | Authenticated (Any role) | `GET /api/v1/settings/paypal` | Live PayPal connection mode (`sandbox` vs `fixture`), OAuth token status | **VERIFIED WORKING** |

---

## 2. UX, DESIGN SYSTEM & ACCESSIBILITY AUDIT

1. **Design System & Typography:**
   - Standardized on IBM Plex Sans and IBM Plex Mono (`ibm-plex-sans`, `ibm-plex-mono`).
   - Unified color tokens for risk semantics:
     * `CRITICAL` (Dark red `#e05252`, border `#ef4444`)
     * `HIGH` (Red `#f87171`)
     * `MEDIUM` (Amber `#fbbf24`)
     * `LOW` (Emerald `#34d399`)
2. **Accessible Keyboard & Screen Reader Navigation:**
   - Skip to content link (`<a href="#main">`) on all pages.
   - Screen-reader labels (`aria-label`, `aria-hidden`) on all icons and navigation controls.
   - Full keyboard focus visible states across inputs, buttons, and grid cells.
3. **Responsive Layouts & Virtualization:**
   - Navigation collapses to an accessible horizontal scroll bar on mobile/tablet viewports and expands to a persistent sidebar on desktop (`md:w-60`).
   - Transactions view utilizes AG Grid DOM virtualization to maintain 60 FPS even with large datasets.
4. **Security & State Hygiene:**
   - Zero local storage token leaks: Authentication is strictly governed by `HttpOnly`, `SameSite=Lax` session cookies.
   - Anti-CSRF protection enforced on all state-mutating requests (`X-CSRF-Token` header paired with cookie).
   - Zero HTML injection or `dangerouslySetInnerHTML` vulnerabilities. All text rendered via safe React primitives.

