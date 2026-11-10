"""Offline construction and wire-compatibility tests: no provider requests."""

import asyncio
import contextlib
import json
from unittest.mock import MagicMock

import httpx2
import pytest
from google.genai.types import HttpRetryOptions
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.core.config import Settings
from app.services.investigation.agent import USER_PROMPT, AgentDeps, build_agent
from app.services.investigation.provider import (
    SentinelGoogleJsonSchemaTransformer,
    SentinelGoogleModel,
    resolve_provider,
)
from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import CaseToolbox


@pytest.fixture(autouse=True)
def _clean_tables():
    yield


@pytest.fixture(scope="module", autouse=True)
def _migrated_database():
    yield


@pytest.mark.parametrize("retries", [0, 1, 2])
def test_google_retry_attempts(retries):
    spec = resolve_provider(
        Settings(
            _env_file=None,
            ai_provider="google",
            ai_model="gemini-3.1-flash-lite",
            ai_api_key="offline-placeholder",
            ai_sdk_max_retries=retries,
        )
    )
    assert spec is not None
    model = spec.build()
    assert isinstance(model, GoogleModel)
    assert isinstance(model, SentinelGoogleModel)
    assert model.client._api_client._http_options.retry_options.attempts == retries + 1


@pytest.mark.parametrize(
    "key,model", [(None, "gemini-3.1-flash-lite"), ("offline-placeholder", None)]
)
def test_google_missing_config(key, model):
    assert (
        resolve_provider(
            Settings(_env_file=None, ai_provider="google", ai_model=model, ai_api_key=key)
        )
        is None
    )


def test_sentinel_google_schema_transformer_inlines_defs():
    from pydantic import TypeAdapter

    raw_schema = TypeAdapter(InvestigationFindings).json_schema()
    assert "$defs" in raw_schema
    transformer = SentinelGoogleJsonSchemaTransformer(raw_schema)
    cleaned = transformer.walk()
    assert "$defs" not in cleaned
    assert "$ref" not in str(cleaned)
    assert "minItems" not in str(cleaned)
    assert "maxItems" not in str(cleaned)


def test_sentinel_google_model_wire_serialization_no_contradiction():
    captured = []

    class MockTransport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            captured.append(json.loads(request.read().decode("utf-8")))
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
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 10,
                    "totalTokenCount": 20,
                },
            }
            return httpx2.Response(
                status_code=200,
                content=json.dumps(dummy).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    provider = GoogleProvider(
        api_key="AIzaSyMockKeyForTesting1234567890",
        retry_options=HttpRetryOptions(attempts=1),
        http_client=httpx2.AsyncClient(transport=MockTransport()),
    )
    model = SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)
    box = MagicMock(spec=CaseToolbox)
    agent = build_agent(model)
    deps = AgentDeps(box=box)

    async def run():
        with contextlib.suppress(Exception):
            await agent.run(USER_PROMPT, deps=deps, model_settings={"timeout": 10.0})

    asyncio.run(run())
    assert len(captured) >= 1
    req = captured[0]
    gen_config = req.get("generationConfig", {})
    # Modality contradiction must be resolved
    assert gen_config.get("responseModalities") is None
    # Tool config must enforce ANY mode to guarantee function/final_result invocation without free-text bypass
    tool_config = req.get("toolConfig", {})
    mode = tool_config.get("functionCallingConfig", {}).get("mode")
    assert mode == "ANY"
    # All schemas must have $defs and $ref inlined
    tools = req.get("tools", [])
    final_tool = next(t for t in tools[0]["functionDeclarations"] if t["name"] == "final_result")
    final_schema_str = json.dumps(final_tool["parameters_json_schema"])
    assert "$defs" not in final_schema_str
    assert "$ref" not in final_schema_str
