"""Budget and adapter checks with scripted models/in-memory HTTP; never paid providers."""

import asyncio
import json
from types import SimpleNamespace
from typing import cast

import httpx2
import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RequestUsage

from app.core.config import AIProvider, Settings
from app.models.enums import InvestigationErrorCategory
from app.services.investigation import runner
from app.services.investigation.provider import ProviderSpec, resolve_provider
from app.services.investigation.toolbox import CaseToolbox


def config(**overrides):
    return Settings(
        _env_file=None,
        hosted_deployment=False,
        allow_webhook_fixtures=False,
        paypal_client_id=None,
        paypal_client_secret=None,
        **overrides,
    )


def empty_box(**methods):
    return cast(
        CaseToolbox,
        SimpleNamespace(refs=set(), identifiers=set(), evidence_text_read={}, **methods),
    )


def findings():
    return {
        "summary": "Continue manual review of the available information.",
        "verified_facts": [],
        "risk_indicators": [],
        "counter_indicators": [],
        "evidence_references": [],
        "missing_information": [],
        "limitations": ["This is a scripted offline test."],
        "recommended_action": "CONTINUE_MANUAL_REVIEW",
        "recommendation_rationale": "An analyst should review the case.",
        "human_approval_required": True,
    }


def scripted(function):
    return ProviderSpec("test", "offline", lambda: FunctionModel(function, model_name="offline"))


def mock_provider(monkeypatch, provider, respond, **overrides):
    settings = config(
        ai_provider=provider,
        ai_model="offline-explicit-model",
        ai_api_key="offline-dummy-key",
        **overrides,
    )
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(respond))
    module = (
        "pydantic_ai.providers._openai_compatible"
        if provider is AIProvider.OPENAI
        else "pydantic_ai.providers.anthropic"
    )
    monkeypatch.setattr(f"{module}.create_async_httpx2_client", lambda: client)
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    spec = resolve_provider(settings)
    assert spec is not None
    return spec, client


@pytest.mark.parametrize(
    "field,value",
    [
        ("ai_sdk_max_retries", -1),
        ("ai_sdk_max_retries", 3),
        ("ai_max_output_tokens", 0),
        ("ai_max_input_bytes", 0),
        ("ai_total_input_bytes_limit", 0),
        ("ai_request_limit", 0),
        ("ai_tool_calls_limit", 0),
        ("ai_total_tokens_limit", 0),
        ("ai_timeout_seconds", 0),
        ("ai_timeout_seconds", float("inf")),
    ],
)
def test_invalid_ai_budgets_fail_configuration(field, value):
    with pytest.raises(ValidationError):
        config(**{field: value})


@pytest.mark.parametrize("provider", [AIProvider.OPENAI, AIProvider.ANTHROPIC])
@pytest.mark.parametrize("status", [401, 429, 503])
def test_sdk_retry_default_is_zero_and_one_attempt_on_errors(monkeypatch, provider, status):
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(
            status,
            json={"type": "error", "error": {"type": "overloaded_error", "message": "private"}},
        )

    spec, client = mock_provider(monkeypatch, provider, respond)
    try:
        model = spec.build()
        assert model.provider.client.max_retries == 0
        fixed = ProviderSpec(spec.provider, spec.model_name, lambda: model)
        with pytest.raises(runner.InvestigationFailed) as caught:
            runner._run_agent(empty_box(), fixed)
        assert caught.value.category == (
            InvestigationErrorCategory.PROVIDER_UNAVAILABLE
            if status == 401
            else InvestigationErrorCategory.PROVIDER_ERROR
        )
        assert len(sent) == 1
        assert sent[0].get("max_completion_tokens", sent[0].get("max_tokens")) == 2048
        assert caught.value.usage["model_requests_attempted"] == 1
        assert caught.value.usage["usage_complete"] is False
        assert "private" not in caught.value.message
    finally:
        asyncio.run(client.aclose())


@pytest.mark.parametrize("adapter", ["chat", "responses"])
def test_offline_adapters_return_typed_output_and_explicit_output_ceiling(monkeypatch, adapter):
    sent = []

    def respond(request):
        sent.append((request.url.path, json.loads(request.content)))
        if adapter == "chat":
            payload = {
                "id": "chatcmpl-offline",
                "object": "chat.completion",
                "created": 0,
                "model": "offline-explicit-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-offline",
                                    "type": "function",
                                    "function": {
                                        "name": "final_result",
                                        "arguments": json.dumps(findings()),
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 30, "total_tokens": 50},
            }
        else:
            payload = {
                "id": "resp_offline",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "offline-explicit-model",
                "output": [
                    {
                        "id": "fc_offline",
                        "type": "function_call",
                        "call_id": "call-offline",
                        "name": "final_result",
                        "arguments": json.dumps(findings()),
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 30, "total_tokens": 50},
            }
        return httpx2.Response(200, json=payload)

    spec, client = mock_provider(monkeypatch, AIProvider.OPENAI, respond)
    try:
        model = spec.build()
        assert isinstance(model, OpenAIChatModel)  # Production factory remains Chat.
        if adapter == "responses":
            model = OpenAIResponsesModel(spec.model_name, provider=model.provider)
        result, usage, denied = runner._run_agent(
            empty_box(), ProviderSpec(spec.provider, spec.model_name, lambda: model)
        )
        assert result.human_approval_required is True
        assert usage["input_tokens"] == 20
        assert usage["output_tokens"] == 30
        assert usage["requests"] == usage["model_requests_attempted"] == 1
        assert usage["usage_complete"] is True
        assert not denied
        path, payload = sent[0]
        assert path == ("/v1/chat/completions" if adapter == "chat" else "/v1/responses")
        assert (
            payload["max_completion_tokens" if adapter == "chat" else "max_output_tokens"] == 2048
        )
        assert "max_tokens" not in payload
        assert payload["tools"]
    finally:
        asyncio.run(client.aclose())


def test_initial_context_rejected_before_any_http_call(monkeypatch):
    sent = []

    def respond(request):
        sent.append(request)
        raise AssertionError("Oversized input must never reach the transport")

    spec, client = mock_provider(monkeypatch, AIProvider.OPENAI, respond, ai_max_input_bytes=1)
    try:
        with pytest.raises(runner.InvestigationFailed) as caught:
            runner._run_agent(empty_box(), spec)
        assert caught.value.category == InvestigationErrorCategory.BUDGET_EXCEEDED
        assert caught.value.usage["model_requests_attempted"] == 0
        assert caught.value.usage["input_requests_rejected"] == 1
        assert caught.value.usage["input_bytes"] == 0
        assert sent == []
    finally:
        asyncio.run(client.aclose())


@pytest.mark.parametrize("budget", ["context", "cumulative", "requests"])
def test_tool_context_and_cumulative_and_logical_limits_stop_next_request(monkeypatch, budget):
    settings = config(
        ai_total_input_bytes_limit=20_000 if budget == "cumulative" else 256_000,
        ai_request_limit=1 if budget == "requests" else 12,
    )
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    attempts = []

    def respond(messages, info):
        attempts.append(messages)
        return ModelResponse(
            parts=[ToolCallPart("get_case_information", {})],
            usage=RequestUsage(input_tokens=17, output_tokens=9),
        )

    box = empty_box(
        case_information=lambda: {
            "untrusted_text": "x" * (100_000 if budget == "context" else 1000)
        }
    )
    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(box, scripted(respond))
    error = caught.value
    assert error.category == InvestigationErrorCategory.BUDGET_EXCEEDED
    assert len(attempts) == 1
    assert error.usage["requests"] == error.usage["model_requests_attempted"] == 1
    assert error.usage["input_requests_rejected"] == (0 if budget == "requests" else 1)
    assert error.usage["input_tokens"] == 17
    assert error.usage["output_tokens"] == 9
    assert error.usage["tool_calls"] == 1
    assert error.usage["usage_complete"] is False


def test_failure_preserves_reported_usage_and_denied_calls(monkeypatch):
    monkeypatch.setattr(runner, "get_settings", lambda: config())
    attempts = 0

    def respond(messages, info):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return ModelResponse(
                parts=[ToolCallPart("refund_payment", {"private": "do-not-persist"})],
                usage=RequestUsage(input_tokens=17, output_tokens=9),
            )
        raise ModelHTTPError(401, "offline", {"secret": "do-not-persist"})

    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(empty_box(), scripted(respond))
    error = caught.value
    assert error.category == InvestigationErrorCategory.PROVIDER_UNAVAILABLE
    assert error.usage["input_tokens"] == 17
    assert error.usage["output_tokens"] == 9
    assert error.usage["requests"] == 1
    assert error.usage["model_requests_attempted"] == 2
    assert [call["name"] for call in error.denied_calls] == ["refund_payment"]
    assert "do-not-persist" not in str(error.usage) + str(error.denied_calls) + error.message


def test_input_budget_includes_schema_not_just_prompt():
    called = []

    def respond(messages, info):
        called.append(True)
        raise AssertionError("Oversized schema must not reach the model")

    model = runner._InputBudgetModel(
        FunctionModel(respond), max_input_bytes=1000, total_input_bytes_limit=2000
    )
    parameters = ModelRequestParameters(
        function_tools=[ToolDefinition(name="read_record", description="x" * 2000)]
    )
    with pytest.raises(runner.UsageLimitExceeded):
        asyncio.run(
            model.request([ModelRequest(parts=[UserPromptPart("Short prompt")])], None, parameters)
        )
    assert model.requests_rejected == 1
    assert model.requests_attempted == 0
    assert called == []


def test_token_limit_failure_keeps_reported_usage(monkeypatch):
    monkeypatch.setattr(runner, "get_settings", lambda: config(ai_total_tokens_limit=20))

    def respond(messages, info):
        return ModelResponse(
            parts=[ToolCallPart("final_result", findings())],
            usage=RequestUsage(input_tokens=21, output_tokens=5),
        )

    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(empty_box(), scripted(respond))
    assert caught.value.category == InvestigationErrorCategory.BUDGET_EXCEEDED
    assert caught.value.usage["input_tokens"] == 21
    assert caught.value.usage["output_tokens"] == 5
    assert caught.value.usage["usage_complete"] is False


def test_success_without_provider_token_usage_is_marked_unknown(monkeypatch):
    def respond(request):
        return httpx2.Response(
            200,
            json={
                "id": "chatcmpl-offline",
                "object": "chat.completion",
                "created": 0,
                "model": "offline-explicit-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-offline",
                                    "type": "function",
                                    "function": {
                                        "name": "final_result",
                                        "arguments": json.dumps(findings()),
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        )

    spec, client = mock_provider(monkeypatch, AIProvider.OPENAI, respond)
    try:
        _, usage, _ = runner._run_agent(empty_box(), spec)
        assert usage["requests"] == 1
        assert usage["input_tokens"] == usage["output_tokens"] == 0
        assert usage["token_usage_available"] is False
        assert usage["usage_complete"] is False
    finally:
        asyncio.run(client.aclose())


@pytest.mark.parametrize("invalid", ["action_claim", "foreign_citation", "schema"])
def test_safeguards_preserve_grounding_and_schema_rejection(monkeypatch, invalid):
    monkeypatch.setattr(runner, "get_settings", lambda: config())

    def respond(messages, info):
        output = findings()
        if invalid == "action_claim":
            output["summary"] = "We have issued the refund."
        elif invalid == "foreign_citation":
            output["verified_facts"] = [
                {
                    "statement": "The other merchant has a payment.",
                    "sources": [{"kind": "transaction", "id": "foreign-private-id"}],
                }
            ]
        else:
            output["human_approval_required"] = False
        return ModelResponse(
            parts=[ToolCallPart("final_result", output)],
            usage=RequestUsage(input_tokens=17, output_tokens=9),
        )

    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(empty_box(), scripted(respond))
    error = caught.value
    assert error.category == (
        InvestigationErrorCategory.INVALID_OUTPUT
        if invalid == "schema"
        else InvestigationErrorCategory.UNSUPPORTED_ASSERTION
    )
    assert error.usage["model_requests_attempted"] == 3
    assert error.usage["input_tokens"] == 51
    assert error.usage["output_tokens"] == 27
    assert error.usage["usage_complete"] is False


def test_final_defense_rejection_preserves_usage_and_denied_audit(monkeypatch):
    monkeypatch.setattr(runner, "get_settings", lambda: config())
    attempts = 0

    def respond(messages, info):
        nonlocal attempts
        attempts += 1
        part = (
            ToolCallPart("refund_payment", {"private": "do-not-persist"})
            if attempts == 1
            else ToolCallPart("final_result", findings())
        )
        return ModelResponse(parts=[part], usage=RequestUsage(input_tokens=17, output_tokens=9))

    def reject(output, box):
        raise runner.FindingsRejected("Final defense rejected the findings.")

    # The agent's validator has its own import; this rejects only the final runner check.
    monkeypatch.setattr(runner, "validate_findings", reject)
    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(empty_box(), scripted(respond))
    error = caught.value
    assert error.category == InvestigationErrorCategory.UNSUPPORTED_ASSERTION
    assert error.usage["requests"] == error.usage["model_requests_attempted"] == 2
    assert error.usage["input_tokens"] == 34
    assert error.usage["output_tokens"] == 18
    assert error.usage["usage_complete"] is False
    assert [call["name"] for call in error.denied_calls] == ["refund_payment"]
    assert error.denied_calls[0]["arguments"] == {}


def test_streaming_cannot_bypass_input_guard():
    called = []

    async def stream(messages, info):
        called.append(True)
        yield "forbidden"

    model = runner._InputBudgetModel(
        FunctionModel(stream_function=stream),
        max_input_bytes=64_000,
        total_input_bytes_limit=256_000,
    )

    async def attempt():
        async with model.request_stream(
            [ModelRequest(parts=[UserPromptPart("Short prompt")])], None, ModelRequestParameters()
        ):
            raise AssertionError("Streaming context must not be entered")

    with pytest.raises(runner.UsageLimitExceeded, match="Streaming investigations are disabled"):
        asyncio.run(attempt())
    assert called == []
    assert model.requests_attempted == 0
    assert model.requests_rejected == 1
