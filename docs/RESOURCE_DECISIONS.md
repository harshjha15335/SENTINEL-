# Resource Decisions

Pinned versions actually installed and tested on 2026-10-10. Full evaluation of every resource from
the research PDFs is in `REFERENCE_ANALYSIS.md`; architecture decisions are in `decisions/`.

## Adopted (in the codebase now)

### Backend (`apps/api/pyproject.toml`)
| Package | Version | Licence | Why |
|---|---|---|---|
| fastapi | 0.143.0 | MIT | Typed REST API with OpenAPI generation (source of the shared contract) |
| uvicorn[standard] | 0.54.0 | BSD-3 | ASGI server |
| sqlalchemy | 2.1.4 | MIT | ORM, typed `Mapped[]` models, row locking for capture/webhooks |
| alembic | 1.20.0 | MIT | Migrations (round-trip tested: downgrade base → upgrade head) |
| pydantic / pydantic-settings | 2.14.0 / 2.15.0 | MIT | Schemas and typed env config |
| psycopg[binary] | 3.3.6 | LGPL-3.0 (library, unmodified, dynamically used) | PostgreSQL driver |
| httpx | 0.28.1 | BSD-3 | PayPal REST client; `MockTransport` for HTTP-level tests |
| argon2-cffi | 25.1.0 | MIT | Password hashing |
| cryptography | 50.0.2 | Apache-2.0/BSD | X.509 + RSA-SHA256 webhook signature verification |
| email-validator | 2.3.0 | Unlicense | `EmailStr` validation |
| pytest / ruff / mypy | 9.1.1 / 0.17.0 / 2.4.0 | MIT | Tests, lint/format, strict typing |

Python: code targets 3.12+ (`requires-python >=3.12`, ruff/mypy target 3.12). This container ran
3.13.16; CI runs 3.12.

### Frontend (`apps/web/package.json`)
| Package | Version | Licence | Why |
|---|---|---|---|
| react / react-dom | 19.3.0 | MIT | UI |
| vite / @vitejs/plugin-react | 8.3.4 / 6.1.2 | MIT | Build/dev server with same-origin `/api` proxy |
| typescript | 5.9.3 | Apache-2.0 | Strict mode; 7.x not yet supported by typescript-eslint |
| tailwindcss / @tailwindcss/vite | 4.3.3 | MIT | Utilities generated from design tokens |
| @radix-ui/react-tooltip | 1.3.0 | MIT | Accessible tooltip primitive (origin badges) |
| ag-grid-community / ag-grid-react | 36.2.0 | MIT | Transaction explorer, Community modules only |
| @tanstack/react-query | 5.104.1 | MIT | Server state |
| react-router-dom | 7.18.4 | MIT | Routing |
| zod / react-hook-form / @hookform/resolvers | 4.6.5 / 7.89.0 / 5.9.1 | MIT | Form validation |
| @paypal/react-paypal-js | 10.6.0 | Apache-2.0 | Official PayPal v6 JS SDK buttons |
| lucide-react | 1.55.0 | ISC | Icons |
| @fontsource/ibm-plex-sans, -mono | 5.3.0 | OFL-1.1 | Typography |
| clsx | 2.1.1 | MIT | Class composition |
| vitest, @testing-library/*, jsdom | 5.0.3, 16.3.3, 30.1.2 | MIT | Unit/integration tests |
| @playwright/test, @axe-core/playwright | 1.64.0, 4.13.0 | Apache-2.0, MPL-2.0 | E2E + accessibility |
| openapi-typescript | 7.13.0 | MIT | Generates `packages/contracts/openapi.ts` |
| eslint, typescript-eslint, eslint-plugin-react-hooks | 10.12.0, 8.71.1, 7.1.1 | MIT | Lint |

## Risk engine (Phase 3, installed)
| Package | Version | Licence | Where | Why |
|---|---|---|---|---|
| xgboost-cpu | 3.4.1 | Apache-2.0 | API runtime | Serves the booster and computes exact TreeSHAP (`pred_contribs`). The CPU-only wheel is ~6 MB; the default `xgboost` wheel pulls a ~200 MB NCCL GPU library the API never uses. |
| numpy | 2.5.4 | BSD-3-Clause | API runtime | Feature matrix for XGBoost |
| scikit-learn | 1.9.1 | BSD-3-Clause | `ml` extra only | Logistic regression, Platt calibration (`FrozenEstimator`), metrics |
| pandas | 3.0.6 | BSD-3-Clause | `ml` extra only | Training frames |
| scipy | 1.18.1 | BSD-3-Clause | `ml` extra only | Required by scikit-learn and xgboost |
| shap | 0.53.0 | MIT | `ml` extra only | Independent check that XGBoost's contributions equal `TreeExplainer`. Not needed at runtime. |

**Model artifact format.** XGBoost JSON plus Platt parameters in `metadata.json`, checked by SHA-256 at load. Pickle and joblib were rejected because unpickling runs arbitrary code, and a plain format is easier to review.

## Committed for upcoming phases (not installed yet)
PydanticAI, pypdf, ReportLab, Radix AlertDialog for approvals (Phase 4) · NetworkX, Recharts (Phase 5).

## Rejected alternatives (short form)
- `paypal-server-sdk`: no Disputes or webhook verification; custom licence. Direct REST instead (decision 0002).
- LangGraph / LangChain / LlamaIndex / Haystack: one agent framework only (PydanticAI); no RAG corpus to justify.
- Celery/Redis/Kafka: DB-backed durable event processing is sufficient now (decision 0004).
- Neo4j / graph DBs: NetworkX until it fails.
- PyMuPDF: AGPL. wkhtmltopdf: archived.
- MUI / Ant Design / Chakra / Bootstrap: competing visual languages; Tailwind + Radix gives one identity.
- AG Grid Enterprise / AG Studio: commercial licence; core product must work without them.
- JWT in localStorage: XSS-exposed; server-side sessions in HttpOnly cookies instead (decision 0003).
