# Investigation Agent Design (plan; not implemented)

**Status: not started (Phase 4).** No AI provider is configured.

- Framework: PydanticAI (typed tools and outputs, provider abstraction). One framework only.
- Tools (read-only, merchant-scoped by the server, never by the model): `get_transaction`, `get_capture_details`, `get_risk_assessment`, `get_transaction_history`, `get_graph_neighbors`, `get_related_disputes`, `get_case_evidence`, `get_merchant_policy`, `get_policy_simulation`. Tool arguments never include a merchant id.
- Output: Pydantic schema (summary, verified facts, risk indicators, counter-indicators, linked activity, evidence ids, missing information, limitations, recommended action, approval_required=true) validated server-side; evidence ids must exist in the case.
- No mutation tools. Refunds and dispute submissions go through approvals executed by backend code.
- Untrusted content (evidence text, webhook bodies) is passed as quoted data, never as instructions; tests include injected instructions in documents.
- Budgets: max tool calls, token and wall-clock limits; every call logged to `investigation_runs.tool_call_log`.
- Provider failure → deterministic, non-LLM case summary labelled "Deterministic summary (AI unavailable)".
