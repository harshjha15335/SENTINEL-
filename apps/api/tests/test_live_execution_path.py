"""Targeted offline tests for the exact Gemini live-test execution path.

Validates that the execution path:
1. Processes valid initial function calls (Turn 1).
2. Immediately stops and records safe diagnostics on HTTP 400 (Invalid Argument).
3. Immediately stops and categorizes as PROVIDER_UNAVAILABLE on HTTP 401 (Unauthenticated).
4. Immediately stops and categorizes as PROVIDER_UNAVAILABLE on HTTP 403 (Permission Denied).
5. Immediately stops and categorizes as PROVIDER_ERROR on HTTP 429 (Rate Limit / Quota Exceeded).
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest
from google.genai.types import HttpRetryOptions
from pydantic_ai.providers.google import GoogleProvider

from app.models.enums import InvestigationErrorCategory
from app.services.investigation.provider import ProviderSpec, SentinelGoogleModel
from app.services.investigation.runner import InvestigationFailed, _run_agent
from app.services.investigation.toolbox import CaseToolbox


@pytest.fixture(autouse=True)
def _clean_tables():
    """No-op database clean for in-memory HTTP tests."""
    yield


@pytest.fixture(scope="module", autouse=True)
def _migrated_database():
    """No-op database migration for in-memory HTTP tests."""
    yield


def _make_spec_with_transport(transport: httpx.AsyncBaseTransport) -> ProviderSpec:
    def build():
        provider = GoogleProvider(
            api_key="AIzaSyMockKeyForOfflinePathTest12345",
            retry_options=HttpRetryOptions(attempts=1),
            http_client=httpx.AsyncClient(transport=transport),
        )
        return SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)

    return ProviderSpec("google", "gemini-3.1-flash-lite", build)


def test_execution_path_stops_on_http_400():
    class Status400Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            err_body = {
                "error": {
                    "code": 400,
                    "message": "Invalid JSON payload received. Unknown name 'invalid_prop'.",
                    "status": "INVALID_ARGUMENT",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.BadRequest",
                            "fieldViolations": [
                                {"field": "generationConfig.invalid", "description": "Invalid"}
                            ],
                        }
                    ],
                }
            }
            return httpx.Response(
                400,
                content=json.dumps(err_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(Status400Transport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec)

    err = exc_info.value
    assert err.category is InvestigationErrorCategory.PROVIDER_ERROR
    assert "HTTP 400" in err.message
    assert err.usage.get("diagnostic") is not None
    assert err.usage["diagnostic"]["status_code"] == 400


def test_execution_path_stops_on_http_401():
    class Status401Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            err_body = {
                "error": {
                    "code": 401,
                    "message": "API key not valid. Please pass a valid API key.",
                    "status": "UNAUTHENTICATED",
                }
            }
            return httpx.Response(
                401,
                content=json.dumps(err_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(Status401Transport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec)

    err = exc_info.value
    assert err.category is InvestigationErrorCategory.PROVIDER_UNAVAILABLE
    assert "HTTP 401" in err.message


def test_execution_path_stops_on_http_403():
    class Status403Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            err_body = {
                "error": {
                    "code": 403,
                    "message": "Method doesn't allow unregistered callers.",
                    "status": "PERMISSION_DENIED",
                }
            }
            return httpx.Response(
                403,
                content=json.dumps(err_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(Status403Transport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec)

    err = exc_info.value
    assert err.category is InvestigationErrorCategory.PROVIDER_UNAVAILABLE
    assert "HTTP 403" in err.message


def test_hard_limit_of_one_request_stops_before_turn_2():
    request_counter = 0

    class MultiTurnMockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            nonlocal request_counter
            request_counter += 1
            if request_counter > 1:
                raise RuntimeError("FAIL: Multiple generation requests attempted!")
            dummy = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"functionCall": {"name": "get_case_information", "args": {}}}
                            ],
                            "role": "model",
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 100,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 120,
                },
            }
            return httpx.Response(
                200,
                content=json.dumps(dummy).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(MultiTurnMockTransport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    # Bounded execution with request_limit=1 must stop after Turn 1
    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec, request_limit=1)

    assert exc_info.value.category is InvestigationErrorCategory.BUDGET_EXCEEDED
    assert request_counter == 1


def test_execution_path_stops_on_http_429():
    class Status429Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            err_body = {
                "error": {
                    "code": 429,
                    "message": "Resource has been exhausted (e.g. check quota).",
                    "status": "RESOURCE_EXHAUSTED",
                }
            }
            return httpx.Response(
                429,
                content=json.dumps(err_body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(Status429Transport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec)

    err = exc_info.value
    assert err.category is InvestigationErrorCategory.PROVIDER_ERROR
    assert "HTTP 429" in err.message


def test_single_request_limiting_transport_enforces_hard_cap():
    import asyncio
    import os
    import sys

    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
    )
    from verify_gemini_entrypoint import SingleRequestLimitingTransport

    class EchoTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})

    transport = SingleRequestLimitingTransport(EchoTransport())
    client = httpx.AsyncClient(transport=transport)

    # 1st request succeeds
    r1 = asyncio.run(client.get("https://example.com/test"))
    assert r1.status_code == 200
    assert transport.request_count == 1

    # 2nd request is hard-blocked at transport boundary
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(client.get("https://example.com/test2"))
    assert "STRICT TRANSPORT CAP VIOLATION" in str(exc_info.value)
    assert transport.request_count == 2
