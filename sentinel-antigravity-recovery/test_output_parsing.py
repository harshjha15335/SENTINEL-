import asyncio
import json
from unittest.mock import MagicMock
import httpx
from google.genai.types import HttpRetryOptions

from app.services.investigation.agent import build_agent, USER_PROMPT, AgentDeps
from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import CaseToolbox
from sentinel_google_model import SentinelGoogleModel
from pydantic_ai.providers.google import GoogleProvider

async def test_output_parsing():
    valid_findings_payload = {
        "summary": "Analyst review completed for synthetic case.",
        "verified_facts": [
            {
                "statement": "The review case was opened by the automated fraud detection engine.",
                "sources": [{"kind": "case", "id": "c96795f1-4180-45de-b606-60f6e27a2160"}]
            }
        ],
        "risk_indicators": [
            {
                "description": "High transaction risk score calculated by XGBoost.",
                "sources": [{"kind": "risk_assessment", "id": "c96795f1-4180-45de-b606-60f6e27a2160"}]
            }
        ],
        "counter_indicators": [],
        "evidence_references": [],
        "missing_information": [],
        "limitations": ["Shadow policy evaluation only."],
        "recommended_action": "CONTINUE_MANUAL_REVIEW",
        "recommendation_rationale": "High calculated risk score requires human review.",
        "human_approval_required": True,
    }

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            dummy = {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "functionCall": {
                                        "name": "final_result",
                                        "args": valid_findings_payload
                                    }
                                }
                            ],
                            "role": "model",
                        },
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 150, "candidatesTokenCount": 250, "totalTokenCount": 400},
            }
            return httpx.Response(status_code=200, content=json.dumps(dummy).encode("utf-8"), headers={"Content-Type": "application/json"})

    provider = GoogleProvider(
        api_key="AIzaSyMockKeyForTesting1234567890",
        retry_options=HttpRetryOptions(attempts=1),
        http_client=httpx.AsyncClient(transport=MockTransport()),
    )
    model = SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)
    box = MagicMock(spec=CaseToolbox)
    box.refs = {("case", "c96795f1-4180-45de-b606-60f6e27a2160"), ("risk_assessment", "c96795f1-4180-45de-b606-60f6e27a2160")}
    box.identifiers = {"c96795f1-4180-45de-b606-60f6e27a2160"}
    agent = build_agent(model)
    deps = AgentDeps(box=box)

    result = await agent.run(USER_PROMPT, deps=deps)
    assert isinstance(result.output, InvestigationFindings)
    assert result.output.recommended_action.value == "CONTINUE_MANUAL_REVIEW"
    assert result.output.human_approval_required is True
    print("Output parsing test PASSED with grounded validation!")

if __name__ == "__main__":
    asyncio.run(test_output_parsing())
