"""Targeted offline tests for the exact Gemini live-test execution path.

Validates that the execution path:
1. Processes valid initial function calls (Turn 1).
2. Immediately stops and records safe diagnostics on HTTP 400 (Invalid Argument).
3. Immediately stops and categorizes as PROVIDER_UNAVAILABLE on HTTP 401 (Unauthenticated).
4. Immediately stops and categorizes as PROVIDER_UNAVAILABLE on HTTP 403 (Permission Denied).
5. Immediately stops and categorizes as PROVIDER_ERROR on HTTP 429 (Rate Limit / Quota Exceeded).
6. Prevents double-decompression errors on gzip/deflate upstream responses.
7. Enforces a strict socket-level limit of ONE outbound generation request.
"""

import asyncio
import gzip
import json
import os
import sys
from unittest.mock import MagicMock

import httpx2
import pytest
from google.genai.types import HttpRetryOptions
from pydantic_ai.providers.google import GoogleProvider

from app.models.enums import InvestigationErrorCategory
from app.services.investigation.provider import ProviderSpec, SentinelGoogleModel
from app.services.investigation.runner import InvestigationFailed, _run_agent
from app.services.investigation.toolbox import CaseToolbox

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
)
from verify_gemini_entrypoint import SingleRequestLimitingTransport, run_auth_verification


@pytest.fixture(autouse=True)
def _clean_tables():
    """No-op database clean for in-memory HTTP tests."""
    yield


@pytest.fixture(scope="module", autouse=True)
def _migrated_database():
    """No-op database migration for in-memory HTTP tests."""
    yield


def _make_spec_with_transport(transport: httpx2.AsyncBaseTransport) -> ProviderSpec:
    def build():
        provider = GoogleProvider(
            api_key="AIzaSyMockKeyForOfflinePathTest12345",
            retry_options=HttpRetryOptions(attempts=1),
            http_client=httpx2.AsyncClient(transport=transport),
        )
        return SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)

    return ProviderSpec("google", "gemini-3.1-flash-lite", build)


def test_execution_path_stops_on_http_400():
    class Status400Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            err_body = {
                "error": {
                    "code": 400,
                    "message": "Invalid JSON payload received. Unknown name 'invalid_prop'.",
                    "status": "INVALID_ARGUMENT",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.BadRequest",
                            "fieldViolations": [
                                {
                                    "field": "tools[0].function_declarations[0].parameters",
                                    "description": "Invalid parameter schema",
                                }
                            ],
                        }
                    ],
                }
            }
            return httpx2.Response(
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


def test_execution_path_stops_on_http_401():
    class Status401Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            err_body = {
                "error": {
                    "code": 401,
                    "message": "API key not valid. Please pass a valid API key.",
                    "status": "UNAUTHENTICATED",
                }
            }
            return httpx2.Response(
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
    class Status403Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            err_body = {
                "error": {
                    "code": 403,
                    "message": "Generative Language API is disabled in project.",
                    "status": "PERMISSION_DENIED",
                }
            }
            return httpx2.Response(
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

    class MultiTurnMockTransport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
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
            return httpx2.Response(
                200,
                content=json.dumps(dummy).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    spec = _make_spec_with_transport(MultiTurnMockTransport())
    box = MagicMock(spec=CaseToolbox)
    box.calls = []

    with pytest.raises(InvestigationFailed) as exc_info:
        _run_agent(box, spec, request_limit=1)

    assert exc_info.value.category is InvestigationErrorCategory.BUDGET_EXCEEDED
    assert request_counter == 1


def test_execution_path_stops_on_http_429():
    class Status429Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            err_body = {
                "error": {
                    "code": 429,
                    "message": "Resource has been exhausted (e.g. check quota).",
                    "status": "RESOURCE_EXHAUSTED",
                }
            }
            return httpx2.Response(
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
    class MockAsyncStream(httpx2.AsyncByteStream):
        def __init__(self, data: bytes):
            self._data = data

        async def __aiter__(self):
            yield self._data

    class EchoTransport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, stream=MockAsyncStream(b'{"status": "ok"}'))

    transport = SingleRequestLimitingTransport(EchoTransport())
    client = httpx2.AsyncClient(transport=transport)

    # 1st request succeeds
    r1 = asyncio.run(client.get("https://example.com/test"))
    assert r1.status_code == 200
    assert transport.request_count == 1

    # 2nd request is hard-blocked at transport boundary
    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(client.get("https://example.com/test2"))
    assert "STRICT TRANSPORT CAP VIOLATION" in str(exc_info.value)
    assert transport.request_count == 2


def test_single_request_limiting_transport_handles_gzip_decompression():
    """Verify that gzip compressed upstream responses decode without double-decompression."""
    raw_dict = {
        "candidates": [
            {
                "content": {
                    "parts": [{"functionCall": {"name": "get_case_information", "args": {}}}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }
    raw_json = json.dumps(raw_dict).encode("utf-8")
    compressed = gzip.compress(raw_json)

    class GzipMockTransport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(
                200,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                content=compressed,
                request=request,
            )

    limiter = SingleRequestLimitingTransport(GzipMockTransport())
    client = httpx2.AsyncClient(transport=limiter)

    resp = asyncio.run(client.get("https://generativelanguage.googleapis.com/test"))
    assert resp.status_code == 200
    assert limiter.request_count == 1
    # Verify downstream reader can read text without zlib header check errors
    assert resp.text is not None
    assert "get_case_information" in resp.text
    # Verify limiter captured parsed JSON safely
    assert limiter.captured_response_json is not None


def test_single_request_limiting_transport_handles_gzip_401():
    """Verify that a 401 gzip response does not trigger zlib decompression errors."""
    raw_401 = (
        b'{"error": {"code": 401, "message": "API key not valid.", "status": "UNAUTHENTICATED"}}'
    )
    compressed = gzip.compress(raw_401)

    class Gzip401Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(
                401,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                content=compressed,
                request=request,
            )

    limiter = SingleRequestLimitingTransport(Gzip401Transport())
    client = httpx2.AsyncClient(transport=limiter)

    resp = asyncio.run(client.get("https://generativelanguage.googleapis.com/test"))
    assert resp.status_code == 401
    assert "UNAUTHENTICATED" in resp.text
    assert limiter.captured_status == 401
    assert limiter.captured_response_json["error"]["code"] == 401


def test_run_auth_verification_offline_200():
    """Verify that run_auth_verification succeeds and decodes model metadata on HTTP 200."""
    dummy_model = {
        "name": "models/gemini-3.1-flash-lite",
        "displayName": "Gemini 3.1 Flash Lite",
        "supportedGenerationMethods": ["generateContent", "countTokens"],
    }
    compressed = gzip.compress(json.dumps(dummy_model).encode("utf-8"))

    class Mock200Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            assert request.method == "GET"
            assert "gemini-3.1-flash-lite" in str(request.url)
            assert "x-goog-api-key" in request.headers
            return httpx2.Response(
                200,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                content=compressed,
                request=request,
            )

    ret = run_auth_verification(
        raw_key="AIzaSyMockKeyForOfflineTest12345",
        mock_transport=Mock200Transport(),
    )
    assert ret == 0


def test_run_auth_verification_offline_401():
    """Verify that run_auth_verification handles and sanitizes 401 UNAUTHENTICATED error."""
    err_body = {
        "error": {
            "code": 401,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "UNAUTHENTICATED",
        }
    }
    compressed = gzip.compress(json.dumps(err_body).encode("utf-8"))

    class Mock401Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(
                401,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                content=compressed,
                request=request,
            )

    ret = run_auth_verification(
        raw_key="AIzaSyInvalidKeyOfflineTest",
        mock_transport=Mock401Transport(),
    )
    assert ret == 1


def test_run_auth_verification_offline_403():
    """Verify that run_auth_verification handles and sanitizes 403 PERMISSION_DENIED error."""
    err_body = {
        "error": {
            "code": 403,
            "message": (
                "Generative Language API has not been used in project 12345 "
                "before or it is disabled."
            ),
            "status": "PERMISSION_DENIED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                    "reason": "SERVICE_DISABLED",
                    "domain": "googleapis.com",
                }
            ],
        }
    }
    compressed = gzip.compress(json.dumps(err_body).encode("utf-8"))

    class Mock403Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(
                403,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                content=compressed,
                request=request,
            )

    ret = run_auth_verification(
        raw_key="AIzaSyForbiddenKeyOfflineTest",
        mock_transport=Mock403Transport(),
    )
    assert ret == 1
