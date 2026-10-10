# Reference Analysis

Sources analysed (both read in full on 2026-10-10):

| Reference | File in repo | Original upload name | Pages |
|---|---|---|---|
| A. Technical research | `docs/research/sentinel-technical-research.pdf` | `Executive Summary 1.pdf` | 17 |
| B. Frontend research | `docs/research/frontend-research.pdf` | `Executive Summary.pdf` | 11 |

Both reports are research aids, not specifications. Their citation markers (`【13†L80-L89】`) point at
a browsing session, not at retrievable URLs, so every claim below that matters to the build was
re-checked against current official documentation or package metadata. **Verified** means checked
in this session against the source named in the row; **Unverified** means we have not confirmed it
and do not rely on it.

Decision vocabulary: **Adopt** (in the codebase now or committed to for the named phase),
**Reference** (read for patterns, not a dependency), **Defer** (credible, revisit when the named
condition holds), **Reject** (not used, reason given).

## 1. Corrections to the reports

| # | Report claim | What is actually true | How SENTINEL handles it |
|---|---|---|---|
| 1 | A, p.15: "Aaryan's SENTINEL Baseline … provided for the PayPal Hackathon. Includes basic PayPal orders and dispute handling logic." | Aaryan Pawar's Fraud Risk Manager was a **Razorpay** hackathon project, has no central PayPal integration, and is All Rights Reserved. | Used only as a functional benchmark; no code, assets or styling reused. See `BASELINE_COMPARISON.md`. |
| 2 | A, p.2 and p.13: webhooks use "HTTPS+HMAC verification". | PayPal webhooks are verified with a **certificate-based RSA-SHA256 signature** over `transmission_id\|transmission_time\|webhook_id\|crc32(raw_body)`, or via the `POST /v1/notifications/verify-webhook-signature` API. Simulator events use webhook id `WEBHOOK_ID` and cannot use the postback API. (developer.paypal.com/api/rest/webhooks/rest/) | `app/services/webhooks.py` implements self-verification with a PayPal-host allowlist for the cert URL; simulator events are stored as `FIXTURE`, never `VERIFIED`. |
| 3 | A, p.4: recommends `Checkout-Python-SDK` (MIT, ~4.5k stars). | That is the legacy `paypal-checkout-serversdk` (last release 1.0.3, Apache-2.0 per PyPI, not MIT). The current official SDK is **`paypal-server-sdk` 2.4.0** under a custom PayPal licence. | Evaluated the current SDK; see decision 0002. |
| 4 | A, p.3: frontend uses the PayPal JS SDK with "React/Vue wrappers" (v5 era). | `@paypal/react-paypal-js` 10.x defaults to the **v6 JS SDK** (`@paypal/react-paypal-js/sdk-v6`, `PayPalProvider` + `PayPalOneTimePaymentButton`, `environment` prop required). Licence Apache-2.0 (npm). | Checkout uses the v6 components. |
| 5 | A, p.9: PyMuPDF is "GPL3". | PyMuPDF is **AGPL-3.0** or commercial (PyPI 1.28.2). | Rejected for evidence extraction; pypdf (BSD-3) preferred. |
| 6 | A, p.10: Neo4j + GDS "Community AGPLv3". | Neo4j Community Edition is GPLv3; GDS has separate licensing. The Python driver is Apache-2.0. Either way it is infrastructure we do not need yet. | Deferred; NetworkX first. |
| 7 | A, p.15: "Grohe/AIEssentials (GitHub) – Sample agent framework". | Could not be located; the report itself hedges ("Include any known open-source agent repo"). | Treated as non-existent. |
| 8 | A, p.16 and B, p.10: sequential Gantt timelines (A spans ~11 weeks). | The deadline is 2026-11-12 12:00 PT (verified on the official rules page), about 4.5 weeks away. | Phases run in parallel with a vertical slice first (see `ARCHITECTURE.md`). |
| 9 | B, §1: names Claude Code skills such as "Theme Factory", "Responsive Tester", "Accessibility Checker" with trigger phrases. | None of those skills are installed in this environment (checked the session's skill list). Their described behaviour maps onto tools we can run directly. | Tokens hand-built in `apps/web/src/styles/tokens.css`; accessibility tested with axe-core in Playwright; responsive checks are Playwright assertions. No third-party skill repos installed. |
| 10 | A and B: star counts (e.g. LangChain 147k, Tailwind 97.9k). | Not re-verified (GitHub API is not reachable from this container). Star counts are not a decision input here. | Ignored. |

## 2. PayPal platform

| Resource | Purpose | Verified / usable | Licence & restrictions | Decision | Module | Why over alternatives | Risks |
|---|---|---|---|---|---|---|---|
| Orders v2 REST | Create, get, capture orders | Verified (API reference) | PayPal developer terms; sandbox free | **Adopt** | `services/paypal/sandbox.py` | Required for checkout; documented `PayPal-Request-Id` idempotency | Order must be approved by buyer before capture |
| Payments v2 REST | Capture details, refunds | Verified | Same | **Adopt** (refund path Phase 5) | gateway `get_capture`, `refund_capture` | Only official refund route | Refunds must stay behind approval workflow |
| Webhooks | Async capture/refund/dispute events | Verified (signature algorithm above) | Same; listener must be HTTPS on 443 | **Adopt** | `services/webhooks.py`, `/api/v1/webhooks/paypal` | Source of truth for out-of-band state changes | Needs public HTTPS URL + registered webhook id |
| Disputes v1 REST | List/get disputes, evidence | Docs reviewed; access is account-dependent | Some operations need extra scopes or account enablement | **Adopt with capability detection** | gateway `list_disputes`, `get_dispute` (tested for 403 handling) | No alternative API | Sandbox dispute creation may not be available; never show simulated outcomes as PayPal's |
| `paypal-server-sdk` 2.4.0 | Official server SDK | Verified from the wheel: controllers = OAuth, Orders, Payments, Vault, Subscriptions, Transaction Search. **No Disputes, no webhook verification.** | Custom PayPal licence (permissive with conditions, not OSI) | **Reference** | n/a | Direct REST via HTTPX covers every needed endpoint uniformly | Mixing SDK + REST would split error handling |
| `paypal-checkout-serversdk` 1.0.3 | Legacy server SDK | Verified on PyPI | Apache-2.0 | **Reject** | n/a | Superseded by Server SDK | Outdated |
| `@paypal/react-paypal-js` 10.6.0 (v6 SDK) | Buyer approval UI | Verified (package README/types; builds and type-checks) | Apache-2.0 | **Adopt** | `features/checkout/CheckoutPage.tsx` | Official React integration | Requires real sandbox client id to render buttons |
| paypal-examples/docs-examples | Reference integrations | Docs reviewed | Open source | **Reference** | Gateway shape | Official patterns | Examples are not production code |
| PayPal Sandbox | Test environment | Verified concept; **no credentials provided yet** | Free developer account | **Adopt** | Whole slice | Required by hackathon | Blocked on credentials (see `IMPLEMENTATION_STATUS.md`) |

## 3. Machine learning and data

| Resource | Purpose | Verified / usable | Licence & restrictions | Decision | Module | Why | Risks |
|---|---|---|---|---|---|---|---|
| scikit-learn 1.9.1 | Baselines, calibration, metrics | Verified (PyPI) | BSD-3 | **Adopt** (Phase 3) | `ml/` | Logistic regression baseline, `CalibratedClassifierCV`, metrics | None notable |
| XGBoost 3.4.1 | Gradient boosting candidate | Verified | Apache-2.0 | **Adopt** (Phase 3) | `ml/training` | Strong tabular baseline, native SHAP TreeExplainer support | Must not be assumed best; compared on validation |
| LightGBM 4.7.0 | Alternative GBM | Verified version | MIT | **Defer** | `ml/training` | Only if XGBoost/LR comparison leaves room | Extra dependency |
| CatBoost 1.2.10 | Categorical-heavy GBM | Verified | Apache-2.0 | **Defer** | — | Our operational features are mostly numeric | Large wheel |
| SHAP 0.53.0 | Local explanations | Verified | MIT | **Adopt** (Phase 3) | risk service + UI | Genuine per-prediction attributions for tree models | Must not be presented as causal |
| PyTorch / PyG / DGL | Neural / GNN models | Not evaluated further | BSD/MIT | **Reject for MVP** | — | No evidence graph features need a GNN; brief forbids premature GNN | Cost, complexity |
| H2O AutoML | AutoML | Not evaluated | Apache-2.0 | **Reject** | — | Opaque selection conflicts with documented methodology | — |
| IEEE-CIS Fraud Detection (Kaggle) | Research benchmark (Track A) | Competition page known; download requires Kaggle account and accepting competition rules | Competition data use rules; **do not redistribute or commit** | **Adopt for Track A** (Phase 3), download script only | `ml/data` | Realistic e-commerce fraud with time offset (`TransactionDT`) enabling a chronological split | Anonymised features do not map to PayPal fields; never claim operational validity |
| Credit Card Fraud (mlg-ulb) | Alternative benchmark | Known dataset (PCA features) | Kaggle-hosted, ODbL per dataset page (to confirm at download) | **Defer** | — | PCA features have no merchant meaning | Limited interpretability |
| PaySim | Synthetic mobile-money simulator | Repository known | Simulator code GPL-3.0 (report agrees) | **Reference** | — | We need PayPal-merchant-shaped synthetic data, not mobile money; GPL code not vendored | Domain mismatch |
| Abrar2652/IEEE-CIS-Fraud-Detection-Project | Example notebook | Not re-verified (GitHub API blocked) | Report says Apache-2.0 | **Reference** | — | Pattern reading only | Notebook leakage patterns must not be copied |
| CTGAN / Synthea | Synthetic tabular data | Not evaluated | MIT / Apache | **Reject** | — | A documented, seeded generator is more transparent for Track B | — |
| Feature Tools / TSFRESH | Automated features | Not evaluated | BSD/MIT | **Reject** | — | Hand-written past-only rolling features are easier to audit for leakage | — |

Track A vs Track B (from the brief) is the governing methodology; see `ML_METHODOLOGY.md`.

## 4. Agentic AI and retrieval

| Resource | Purpose | Verified / usable | Licence | Decision | Module | Why | Risks |
|---|---|---|---|---|---|---|---|
| PydanticAI 2.55.0 | Typed tool-calling agent | Verified (PyPI, production/stable) | MIT | **Adopt** (Phase 4) | `services/agents` | Pydantic-typed tools and outputs match our FastAPI/Pydantic stack; model-provider abstraction built in; small surface | Pin version; validate outputs ourselves too |
| LangGraph 1.2.14 | Graph-structured agents | Verified | MIT | **Reject for now** | — | Our investigation is a bounded, mostly linear tool sequence; LangGraph adds a second state model | Revisit only if branching workflows appear |
| LangChain 1.4.4 | Chains/tools | Verified | MIT | **Reject** | — | Overlaps PydanticAI; large dependency tree | — |
| LlamaIndex 0.14.25 | RAG | Verified | MIT | **Reject** | — | Evidence per case is small; direct retrieval from Postgres with citations is simpler and auditable | — |
| Haystack | RAG pipelines | Not evaluated | Apache-2.0 | **Reject** | — | Same reason | — |
| Vector DBs (Weaviate, Qdrant, Pinecone) | Embedding search | Not evaluated | Mixed | **Defer** | — | No corpus large enough to justify; pgvector is the path if needed | Extra infra |
| OpenAI Functions | Provider-specific tool calling | — | Proprietary | **Reject** as a framework | — | Provider abstraction via PydanticAI instead | Lock-in |
| AutoGPT / ReAct demos | Autonomous agents | — | MIT | **Reject** | — | SENTINEL forbids autonomous financial action | Safety |

## 5. Evidence and documents

| Resource | Purpose | Verified | Licence | Decision | Why / risk |
|---|---|---|---|---|---|
| pypdf 6.20.0 | PDF text extraction | Verified | BSD-3 | **Adopt** (Phase 4) | Permissive, pure Python, no code execution |
| ReportLab 5.0.1 | Evidence packet PDF generation | Verified | BSD | **Adopt** (Phase 4) | Mature, permissive |
| PyMuPDF 1.28.2 | PDF parse/render | Verified | **AGPL-3.0** or commercial | **Reject** | Licence obligations for a hosted service |
| Tesseract OCR | OCR for scanned evidence | Known | Apache-2.0 | **Defer** | Only if scanned uploads appear; system binary adds deploy weight |
| EasyOCR | Deep-learning OCR | — | Apache-2.0 | **Reject** | Heavy (PyTorch) |
| Apache Tika | Multi-format extraction | — | Apache-2.0 | **Reject** | Needs a JVM service |
| wkhtmltopdf / PDFKit | HTML→PDF | — | LGPL; wkhtmltopdf is archived upstream | **Reject** | Unmaintained |
| AWS Textract / Google Vision | Cloud OCR | — | Proprietary, paid | **Reject** | Cost, data egress |
| ExifTool / ClamAV | Metadata / AV | — | GPL | **Defer** | Validate type, size and SHA-256 first; AV only if deployment host provides it |
| python-magic | MIME sniffing | — | MIT (needs libmagic) | **Defer** | Magic-byte checks for PDF/PNG/JPEG can be done in-code |

## 6. Graph analysis

| Resource | Purpose | Verified | Licence | Decision | Why |
|---|---|---|---|---|---|
| NetworkX 3.7 | Graph features, components | Verified | BSD-3 | **Adopt** (Phase 5) | In-process, enough for merchant-scale graphs |
| Neo4j + GDS | Graph DB + algorithms | Driver verified (Apache-2.0); server licensing per §1 | GPLv3 / commercial | **Defer** | Only if NetworkX demonstrably fails |
| ArangoDB, TigerGraph | Graph DBs | — | Mixed / proprietary | **Reject** | Infra for appearance |
| Gephi / Cytoscape desktop | Manual viz | — | GPL | **Reject** | We need in-app visualisation |
| Neo4j fraud blog | Pattern reference | — | — | **Reference** | Ideas for graph features only |

## 7. Backend, jobs, monitoring, DevOps

| Resource | Decision | Notes |
|---|---|---|
| FastAPI 0.143.0, Pydantic 2.14, SQLAlchemy 2.1.4, Alembic 1.20, psycopg 3.3.6, HTTPX 0.28.1 | **Adopt** (in code) | All verified installed and tested. |
| argon2-cffi 25.1.0, cryptography 50.0.2 | **Adopt** | Password hashing; webhook signature verification. |
| PostgreSQL 16 | **Adopt** | Local server used for all tests this session. |
| Flask, Django, Express | **Reject** | FastAPI covers needs. |
| Celery + RabbitMQ/Redis | **Defer** | DB-backed event table + worker (`app/workers/events.py`) is durable at current volume. Revisit if scoring/OCR jobs need concurrency. |
| Kafka | **Reject** | No streaming volume to justify. |
| Airflow / Prefect | **Reject** | Training is a CLI pipeline, not a scheduled DAG. |
| Prometheus + Grafana (AGPLv3) | **Defer** | Structured JSON logs, correlation ids, health/readiness first. |
| Sentry | **Defer** | Optional if hosted provider lacks error capture. |
| Elastic / OpenSearch | **Reject** | Not needed; Elastic is a sponsor but adds no core value now. |
| Docker Compose | **Adopt** | `compose.yaml` for Postgres (docker not available in this container; Postgres run natively here). |
| GitHub Actions | **Adopt** | `.github/workflows/ci.yml`. |
| Terraform / CloudFormation, PagerDuty | **Reject** | Hosted PaaS is enough. |
| Postman / Newman | **Defer** | Postman is a sponsor tool; pytest covers API tests. A collection may be added for judges. |
| Render (backend), Vercel (frontend) | **Defer to Phase 6** | Render is also a sponsor. |

## 8. Frontend (Reference B)

| Resource | Purpose | Verified | Licence | Decision | Why over alternatives / risks |
|---|---|---|---|---|---|
| React 19.3 + Vite 8.3 + TypeScript 5.9.3 | App runtime and build | Verified (installed, builds) | MIT | **Adopt** | TS 7.0 exists but typescript-eslint 8.71 supports `<6.1`, so 5.9.3 is pinned. |
| Tailwind CSS 4.3 | Styling via `@theme` tokens | Verified | MIT | **Adopt** | Tokens generate utilities; no runtime. |
| Radix UI primitives (Tooltip now; AlertDialog in Phase 4) | Accessible behaviour, unstyled | Verified | MIT | **Adopt** | Keeps our visual identity; audited a11y behaviour. |
| AG Grid Community 36.2 | Transaction explorer | Verified (MIT on npm) | MIT | **Adopt** | Only Community modules are registered. Bundle is large (~1.1 MB chunk, lazy-loaded); trimming modules is a follow-up. |
| AG Studio (`ag-studio-react` 3.0.0) | Embedded analytics, sponsor prize | npm licence field: **Commercial**; quick-start links to enterprise licence pages | Commercial | **Defer** | Core product must not depend on it. Revisit as an optional, isolated dashboard only after confirming hackathon licence terms with AG Grid. |
| Recharts 3.10 | Charts | Verified version | MIT | **Defer** (Phase 3 trend charts) | Not yet needed; avoids an unused dependency. |
| TanStack Query 5, React Router 7, Zod 4, React Hook Form 7, Lucide | Data, routing, validation, forms, icons | Verified | MIT / ISC | **Adopt** | Standard, small. |
| IBM Plex Sans + Mono (`@fontsource`) | Typography | Verified | OFL-1.1 | **Adopt** | Distinct, legible, tabular figures; self-hosted. |
| MUI, Ant Design, Chakra, Bootstrap, Bulma, Foundation, UIKit, Semantic UI, Fluent UI, Flowbite, DaisyUI | Component libraries / CSS frameworks | Not installed | MIT/Apache | **Reject** | Each imposes its own visual language; we need one coherent finance identity on Tailwind + Radix. |
| Headless UI, React Aria, Reach UI | Headless primitives | — | MIT/Apache | **Reject** | Radix chosen; one primitive library. |
| Heroicons | Icons | — | MIT | **Reject** | Lucide chosen. |
| Storybook | Component docs | — | MIT | **Defer** | Only if time permits after Phase 4. |
| Next.js, Astro, 11ty, CRA, Vue, Angular, Vuetify, Quasar, BootstrapVue | Frameworks | — | MIT | **Reject** | SPA behind auth; Vite is enough; CRA is deprecated. |
| USWDS, GitHub Primer, design-system-starter | Design systems | — | MIT | **Reference** | Token and documentation patterns only. |
| Figma UI kits | Design assets | — | Varies | **Reject** | Original assets only. |
| Vitest 5, Testing Library 16, Playwright 1.64, axe-core (`@axe-core/playwright` 4.13) | Testing | Verified (all run green) | MIT / Apache / MPL-2.0 | **Adopt** | axe runs WCAG 2.0/2.1/2.2 A+AA tags on every e2e page. |
| react-three-fiber | 3D | — | MIT | **Reject** | No product reason. |
| Motion libraries (Framer Motion, GSAP) | Animation | — | MIT / custom | **Reject for now** | CSS transitions with motion tokens and `prefers-reduced-motion`. |

## 9. Claude Code skills (Reference B §1)

Inspected the session's available skills: `dataviz`, `artifact-*`, `run`, `code-review`,
`security-review`, `simplify`, `session-start-hook`, document skills and others. None of
"Frontend Design", "Theme Factory", "Design System Builder", "UI Component Generator",
"Responsive Tester", "Site Audit", "Accessibility Checker", "Motion Design System" or "Screenshot
Testing" is installed. No third-party skill repository was installed, so no external scripts were
executed. Equivalent outcomes are produced with first-party tooling: hand-authored tokens,
axe-core + Playwright for accessibility, Playwright viewport assertions and screenshots for
responsive QA. `security-review` and `dataviz` are relevant for Phases 3 and 6.
