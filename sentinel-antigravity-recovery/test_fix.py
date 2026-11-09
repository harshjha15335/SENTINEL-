import asyncio
import json
from dataclasses import replace
from unittest.mock import MagicMock
from typing import Any
import httpx
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from google.genai.types import HttpRetryOptions, FunctionCallingConfigMode

from app.services.investigation.agent import build_agent, USER_PROMPT, AgentDeps
from app.services.investigation.toolbox import CaseToolbox

class SentinelGoogleJsonSchemaTransformer(GoogleJsonSchemaTransformer):
    def __init__(self, schema, *, strict=None, **kwargs):
        super().__init__(
            schema,
            strict=strict,
            prefer_inlined_defs=True,
            simplify_nullable_unions=True,
        )

    def transform(self, schema):
        schema = super().transform(schema)
        # Strip keywords that Gemini's OpenAPI 3.0 subset parser rejects
        schema.pop("minItems", None)
        schema.pop("maxItems", None)
        return schema

class SentinelGoogleModel(GoogleModel):
    def prepare_request(self, model_settings, model_request_parameters):
        model_settings, model_request_parameters = super().prepare_request(model_settings, model_request_parameters)
        
        def clean_tool(tool_def):
            transformer = SentinelGoogleJsonSchemaTransformer(tool_def.parameters_json_schema, strict=tool_def.strict)
            clean_schema = transformer.walk()
            return replace(tool_def, parameters_json_schema=clean_schema)

        model_request_parameters = replace(
            model_request_parameters,
            function_tools=[clean_tool(t) for t in model_request_parameters.function_tools],
            output_tools=[clean_tool(t) for t in model_request_parameters.output_tools],
        )
        return model_settings, model_request_parameters

    async def _build_content_and_config(self, messages, model_settings, model_request_parameters):
        contents, config = await super()._build_content_and_config(
            messages, model_settings, model_request_parameters
        )
        # Fix Bug 1: Pydantic-AI 2.55.0 bug where response_modalities is sent as ['TEXT']
        # even when tool-use is forced or tools are present.
        if config.get("tools"):
            config["response_modalities"] = None

        # Fix Bug 2: Upgrade mode: ANY to VALIDATED (or AUTO)
        tool_config = config.get("tool_config")
        if tool_config and "function_calling_config" in tool_config:
            fcc = tool_config["function_calling_config"]
            if fcc.get("mode") == FunctionCallingConfigMode.ANY:
                if self.profile.get("google_supports_strict_tool_definition", False):
                    fcc["mode"] = FunctionCallingConfigMode.VALIDATED
                else:
                    fcc["mode"] = FunctionCallingConfigMode.AUTO

        return contents, config

captured = []

class MockTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        content = request.read()
        captured.append({
            "url": str(request.url),
            "body": json.loads(content.decode("utf-8")),
        })
        dummy = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "get_case_information", "args": {}}}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "totalTokenCount": 120},
        }
        return httpx.Response(status_code=200, content=json.dumps(dummy).encode("utf-8"), headers={"Content-Type": "application/json"})

async def run_test():
    provider = GoogleProvider(
        api_key="AIzaSyMockKeyForTesting1234567890",
        retry_options=HttpRetryOptions(attempts=1),
        http_client=httpx.AsyncClient(transport=MockTransport()),
    )
    model = SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)
    box = MagicMock(spec=CaseToolbox)
    agent = build_agent(model)
    deps = AgentDeps(box=box)

    try:
        await agent.run(
            USER_PROMPT,
            deps=deps,
            model_settings={
                "timeout": 15.0,
                "temperature": 1.0,
                "max_tokens": 2048,
            }
        )
    except Exception as e:
        print("Run error:", e)

    if captured:
        body = captured[0]["body"]
        print("=== VERIFICATION OF FIXED REQUEST BODY ===")
        print("URL:", captured[0]["url"])
        print("responseModalities in generationConfig:", body.get("generationConfig", {}).get("responseModalities"))
        print("toolConfig:", body.get("toolConfig"))
        tools = body.get("tools", [])
        fd = tools[0]["functionDeclarations"]
        final_fd = next(f for f in fd if f["name"] == "final_result")
        schema_str = json.dumps(final_fd["parameters_json_schema"])
        print("Has $defs in final_result:", "$defs" in schema_str)
        print("Has $ref in final_result:", "$ref" in schema_str)
        print("Has minItems/maxItems:", "minItems" in schema_str or "maxItems" in schema_str)
        print("final_result schema size:", len(schema_str))

        with open("sentinel-antigravity-recovery/fixed_request_body.json", "w") as f:
            json.dump(body, f, indent=2)

asyncio.run(run_test())
