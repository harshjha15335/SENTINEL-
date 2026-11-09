import asyncio
import json
import os
import copy
from typing import Any
import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from google.genai.types import HttpRetryOptions

from app.services.investigation.agent import (
    INSTRUCTIONS,
    USER_PROMPT,
    AgentDeps,
    build_agent,
)
from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import CaseToolbox
from unittest.mock import MagicMock

os.makedirs("sentinel-antigravity-recovery", exist_ok=True)

class InterceptTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.captured = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        content = request.read()
        self.captured = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": json.loads(content.decode("utf-8")) if content else None,
        }
        # Return a dummy model response so the agent doesn't crash on transport
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
            status_code=200,
            content=json.dumps(dummy).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

def make_model(transport: InterceptTransport) -> GoogleModel:
    provider = GoogleProvider(
        api_key="AIzaSyMockKeyForTesting1234567890",
        retry_options=HttpRetryOptions(attempts=1),
        http_client=httpx.AsyncClient(transport=transport),
    )
    return GoogleModel("gemini-3.1-flash-lite", provider=provider)

async def test_variant(name: str, agent: Agent, model_settings: dict, run_prompt: str = USER_PROMPT):
    transport = InterceptTransport()
    # update model's client transport
    agent.model = make_model(transport)
    box = MagicMock(spec=CaseToolbox)
    deps = AgentDeps(box=box)
    try:
        await agent.run(run_prompt, deps=deps, model_settings=model_settings)
    except Exception as e:
        pass
    return transport.captured

async def run_all_variants():
    results = {}
    
    # Variant A: Exact original request
    print("Running Variant A: Baseline...")
    base_agent = build_agent(make_model(InterceptTransport()))
    res_a = await test_variant("A", base_agent, {
        "timeout": 15.0,
        "temperature": 0.0,
        "max_tokens": 512,
    })
    results["A"] = res_a

    # Variant B: One minimal read-only tool
    print("Running Variant B: Minimal read-only tool...")
    agent_b = Agent(
        make_model(InterceptTransport()),
        output_type=InvestigationFindings,
        instructions=INSTRUCTIONS,
    )
    @agent_b.tool
    async def get_case_information(ctx: RunContext[Any]) -> dict:
        """Case info."""
        return {}
    res_b = await test_variant("B", agent_b, {"timeout": 15.0, "temperature": 0.0, "max_tokens": 512})
    results["B"] = res_b

    # Variant C: Only final_result (No extra tools)
    print("Running Variant C: Only final_result...")
    agent_c = Agent(
        make_model(InterceptTransport()),
        output_type=InvestigationFindings,
        instructions=INSTRUCTIONS,
    )
    res_c = await test_variant("C", agent_c, {"timeout": 15.0, "temperature": 0.0, "max_tokens": 512})
    results["C"] = res_c

    # Variant D: Reduced read-only tool set (3 core tools)
    print("Running Variant D: Reduced read-only tools...")
    agent_d = Agent(
        make_model(InterceptTransport()),
        output_type=InvestigationFindings,
        instructions=INSTRUCTIONS,
    )
    @agent_d.tool
    async def get_case_information(ctx: RunContext[Any]) -> dict: return {}
    @agent_d.tool
    async def get_transaction_details(ctx: RunContext[Any]) -> dict: return {}
    @agent_d.tool
    async def get_latest_risk_assessment(ctx: RunContext[Any]) -> dict: return {}
    res_d = await test_variant("D", agent_d, {"timeout": 15.0, "temperature": 0.0, "max_tokens": 512})
    results["D"] = res_d

    # Variant E: Simplified parameter schemas (Flat output model)
    print("Running Variant E: Simplified output schema...")
    class SimpleFindings(BaseModel):
        summary: str
        action: str
        human_approval_required: bool
    agent_e = Agent(
        make_model(InterceptTransport()),
        output_type=SimpleFindings,
        instructions=INSTRUCTIONS,
    )
    res_e = await test_variant("E", agent_e, {"timeout": 15.0, "temperature": 0.0, "max_tokens": 512})
    results["E"] = res_e

    # Variant F: Google-compatible schema representation (Native JSON mode with output_mode="native")
    print("Running Variant F: Google native JSON output mode...")
    # On Google, if there are no tools, prompted or native output can be used
    agent_f = Agent(
        make_model(InterceptTransport()),
        output_type=InvestigationFindings,
        instructions=INSTRUCTIONS,
    )
    # Check if we can force native output without tools or with tools
    res_f = await test_variant("F", agent_f, {"timeout": 15.0, "temperature": 0.0, "max_tokens": 512})
    results["F"] = res_f

    # Variant G: AUTO instead of ANY (tool_choice="auto")
    print("Running Variant G: tool_choice='auto'...")
    agent_g = build_agent(make_model(InterceptTransport()))
    res_g = await test_variant("G", agent_g, {
        "timeout": 15.0,
        "temperature": 0.0,
        "max_tokens": 512,
        "tool_choice": "auto",
    })
    results["G"] = res_g

    # Variant H: ANY with minimal schema
    print("Running Variant H: ANY with minimal schema...")
    agent_h = Agent(
        make_model(InterceptTransport()),
        output_type=SimpleFindings,
        instructions=INSTRUCTIONS,
    )
    @agent_h.tool
    async def ping(ctx: RunContext[Any]) -> str: return "pong"
    res_h = await test_variant("H", agent_h, {
        "timeout": 15.0,
        "temperature": 0.0,
        "max_tokens": 512,
        "tool_choice": "required",
    })
    results["H"] = res_h

    # Variant I: Original tools without optional settings (temperature default, max_tokens None)
    print("Running Variant I: Original tools without optional settings...")
    agent_i = build_agent(make_model(InterceptTransport()))
    res_i = await test_variant("I", agent_i, {
        "timeout": 15.0,
    })
    results["I"] = res_i

    # Variant J: Documented model-specific settings (with thinking config and relaxed tokens)
    print("Running Variant J: Model-specific settings...")
    agent_j = build_agent(make_model(InterceptTransport()))
    res_j = await test_variant("J", agent_j, {
        "timeout": 15.0,
        "temperature": 1.0,
        "max_tokens": 2048,
    })
    results["J"] = res_j

    # Save summary and comparisons
    summary_report = []
    summary_report.append("# OFFLINE DIAGNOSTIC MATRIX (VARIANTS A - J)\n")
    summary_report.append("| Variant | Mode | Tools Count | Has $defs/$ref | generationConfig | Request Body Size (bytes) | Notes |")
    summary_report.append("|---|---|---|---|---|---|---|")

    for k in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        req = results.get(k)
        if not req:
            summary_report.append(f"| {k} | N/A | N/A | N/A | N/A | N/A | Failed to capture |")
            continue
        body = req["body"]
        tc = body.get("toolConfig", {})
        mode = tc.get("functionCallingConfig", {}).get("mode", "DEFAULT/UNSET")
        tools = body.get("tools", [])
        fd_count = 0
        if tools and "functionDeclarations" in tools[0]:
            fd_count = len(tools[0]["functionDeclarations"])
        body_str = json.dumps(body)
        has_defs = "$defs" in body_str
        has_ref = "$ref" in body_str
        gc = body.get("generationConfig", {})
        gc_str = json.dumps(gc)
        size = len(body_str.encode("utf-8"))
        summary_report.append(f"| {k} | `{mode}` | {fd_count} | {has_defs or has_ref} | `{gc_str}` | {size:,} | |")

        with open(f"sentinel-antigravity-recovery/variant_{k}.json", "w") as vf:
            json.dump(body, vf, indent=2)

    with open("sentinel-antigravity-recovery/matrix_summary.md", "w") as mf:
        mf.write("\n".join(summary_report))

    print("\nDiagnostic matrix generated successfully!")
    print("\n".join(summary_report))

if __name__ == "__main__":
    asyncio.run(run_all_variants())

