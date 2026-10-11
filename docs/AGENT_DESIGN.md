# Investigation Agent Design

**Status (2026-10-11, session 3): implemented and tested with scripted models. Not yet run
against a real AI provider** — no provider credentials exist in the build environment, so the
provider-backed integration test is skipped. Without credentials SENTINEL produces a
deterministic summary, labelled as such.

## Flow
1. `POST /cases/{id}/investigations` (ADMIN/ANALYST, CSRF). The server loads the case through the
   principal's merchant (`get_case`, row lock), applies the concurrency policy and creates a
   `QUEUED` `investigation_runs` row (202).
2. A background task (`runner.execute`) opens its own DB session, marks the run `RUNNING`,
   re-loads the case by the run's own `merchant_id`/`case_id`, and builds a `CaseToolbox`.
3. Mode `AI_AGENT` if a provider is configured (and the caller did not ask for deterministic);
   otherwise `DETERMINISTIC`.
4. The output is validated (`validate_findings`), then saved with tool-call metadata, the set of
   records read (`source_refs`), usage, timing and status. Failures are saved as `FAILED` with an
   error category; the case and earlier runs are never touched.

## Framework and provider abstraction
- PydanticAI 2.55 (`pydantic-ai-slim[anthropic,openai]`), typed tools and `output_type`.
- `services/investigation/provider.py`: `ProviderSpec(provider, model_name, build)`.
  `SENTINEL_AI_PROVIDER=none|anthropic|openai`, `SENTINEL_AI_API_KEY`, `SENTINEL_AI_MODEL`
  (Anthropic default `claude-sonnet-5-5`; OpenAI requires an explicit model). Missing key ⇒ no
  provider ⇒ deterministic summary. Tests install scripted `FunctionModel`s with
  `override_provider`; real provider behaviour is covered only by `tests/integration/`.
- Budgets: `ai_request_limit` (12), `ai_tool_calls_limit` (24), `ai_total_tokens_limit`
  (120k), wall clock `ai_timeout_seconds` (90, `asyncio.wait_for` + per-request timeout),
  temperature 0, prompt version `investigation-v1`.

## Tools (all read-only, bound to one authorised case)
Tool signatures contain no merchant, case or transaction id; scope comes from the run row.

| Tool | Returns |
|---|---|
| `get_case_information` | status, priority, source, due date, origin |
| `get_transaction_details` | amount, status, PayPal ids, payer reference, timestamps, origin + provenance note |
| `get_latest_risk_assessment` | score, band, shadow decision, top TreeSHAP drivers, limitations |
| `get_payer_history(limit)` | earlier payments of *this payment's* payer reference, same merchant + origin, past only |
| `get_case_notes` | notes as `untrusted_text` |
| `list_case_evidence` | evidence metadata, uploader's description as `untrusted_description`, checklist |
| `read_evidence_text(evidence_id)` | extracted text as `untrusted_content` (ids outside the case ⇒ `denied`) |
| `get_capture_information` | stored provider summary + webhook events (no live PayPal call) |
| `get_graph_neighbors`, `get_related_disputes`, `get_merchant_policy` | `{"available": false}` until Phase 5 |

Each call is logged (`name`, sanitised args, outcome `ok|denied|unavailable`, duration, record
refs). Calls to tools that do not exist (e.g. a model asking for `refund_payment`) are recorded as
`denied`; there is nothing to execute.

## Output schema (`InvestigationFindings`, `extra="forbid"`)
`summary`, `verified_facts[{statement, sources[]}]`, `risk_indicators[]`, `counter_indicators[]`,
`evidence_references[{evidence_id, relevance, excerpt?}]`, `missing_information[]`,
`limitations[]`, `recommended_action` (enum), `recommendation_rationale`,
`human_approval_required: Literal[True]`.

## Grounding checks (`validation.py`), applied to AI and deterministic output
- Every cited `(kind, id)` must be a record a tool returned in this run.
- Every evidence reference must be evidence of this case that the run retrieved; excerpts must
  appear verbatim (whitespace-normalised) in that evidence's extracted text.
- Any UUID, PayPal-style id or `SIM-`/`SYN-` reference in free text must have been returned by a
  tool.
- Text that claims an action was taken ("we have issued the refund", "evidence was submitted")
  is rejected.
Failures go back to the model as a retry (up to 2); persistent failure ⇒ `UNSUPPORTED_ASSERTION`.
Schema failures ⇒ `INVALID_OUTPUT`.

## Untrusted content
Notes and evidence text only ever reach the model inside tool results, under `untrusted_*` keys
with a notice. Instructions and the user prompt are constants. A test uploads a PDF containing an
injection and asserts it appears only in a tool return, and that an output obeying it is rejected.

## Concurrency and failure policy
- At most one `QUEUED`/`RUNNING` run per case: case row lock + partial unique index. A second
  start returns 409 with the active run id. Runs active longer than
  `investigation_stale_seconds` (600) are marked `FAILED/ABANDONED` before a new one starts.
- Error categories: `PROVIDER_UNAVAILABLE` (401/403 or not configured), `PROVIDER_TIMEOUT`,
  `PROVIDER_ERROR`, `INVALID_OUTPUT`, `UNSUPPORTED_ASSERTION`, `BUDGET_EXCEEDED`, `ABANDONED`,
  `INTERNAL`. Messages never include provider bodies or keys.
- Runs execute in-process (FastAPI background task). A process restart abandons a running run;
  the stale rule recovers it. A durable job queue is a Phase 6 option.

## Deterministic fallback
`deterministic.py` calls the same toolbox and builds findings from records by fixed rules
(SHAP drivers ⇒ indicators, payer history, evidence checklist ⇒ missing information). Labelled
**"Deterministic summary — AI provider unavailable"** (or "— AI not used" when chosen explicitly),
`generated_by_ai=false`, and never described as AI analysis in the API, UI or packet.

## What the agent cannot do
No mutation tools; no payment, refund, dispute or messaging capability; no access to other
merchants' data; recommendations only. Financial actions go through the approval workflow and,
in Phase 4, are recorded as intent only (`docs/SECURITY.md`).
