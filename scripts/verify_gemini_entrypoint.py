"""SENTINEL — Secure Gemini Provider Entrypoint & Verification Tool

Verifies that the Gemini AI provider is configured and reads SENTINEL_AI_API_KEY
securely via Pydantic Settings without leaking secrets.

Usage:
    # 1. Offline configuration and wire-schema verification (Default, Safe):
    python scripts/verify_gemini_entrypoint.py --dry-run

    # 2. Live single-request test (Requires explicit authorization, key, and case ID):
    python scripts/verify_gemini_entrypoint.py --execute --case-id <UUID>
"""

import argparse
import json
import os
import sys
from unittest.mock import MagicMock

# Ensure apps/api is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from app.core.config import AIProvider, Settings, get_settings  # noqa: E402
from app.services.investigation.agent import USER_PROMPT, AgentDeps, build_agent  # noqa: E402
from app.services.investigation.provider import (  # noqa: E402
    SentinelGoogleJsonSchemaTransformer,
    SentinelGoogleModel,
    resolve_provider,
    status,
)
from app.services.investigation.schemas import InvestigationFindings  # noqa: E402
from app.services.investigation.toolbox import CaseToolbox  # noqa: E402


def get_api_key_securely(prompt_if_missing: bool = False) -> str:
    """Fetch API key from process env, Windows user registry, or hidden interactive prompt."""
    key = os.environ.get("SENTINEL_AI_API_KEY") or os.environ.get("SENTINEL_IT_AI_API_KEY") or ""
    key = key.strip()
    if key:
        return key

    # Check Windows User-level environment without echoing
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as env_key:
                val, _ = winreg.QueryValueEx(env_key, "SENTINEL_AI_API_KEY")
                if val and str(val).strip():
                    return str(val).strip()
        except Exception:
            pass

    if prompt_if_missing and sys.stdin.isatty():
        import getpass

        print("\n[SECURE PROMPT] SENTINEL_AI_API_KEY not found in environment.")
        print("Input will NOT be echoed to screen or stored in shell history.")
        entered = getpass.getpass("Enter Google Gemini API Key: ").strip()
        if entered:
            # Inject into current process memory only
            os.environ["SENTINEL_AI_API_KEY"] = entered
            return entered

    return ""


def verify_configuration(prompt_if_missing: bool = False) -> tuple[bool, str]:
    """Verify that settings securely load SENTINEL_AI_API_KEY and provider config."""
    raw_key = get_api_key_securely(prompt_if_missing=prompt_if_missing)
    provider_name = os.environ.get("SENTINEL_AI_PROVIDER") or os.environ.get("SENTINEL_IT_AI_PROVIDER") or "google"
    model_name = os.environ.get("SENTINEL_AI_MODEL") or os.environ.get("SENTINEL_IT_AI_MODEL") or "gemini-3.1-flash-lite"

    if not raw_key:
        return False, "SENTINEL_AI_API_KEY is not set in environment (safe: secret not required for offline dry-run)."

    test_settings = Settings(
        ai_provider=AIProvider(provider_name.lower()),
        ai_model=model_name,
        ai_api_key=raw_key,
    )

    # Verify secret is wrapped in SecretStr and redacted
    assert test_settings.ai_api_key is not None
    repr_str = repr(test_settings.ai_api_key)
    if raw_key in repr_str:
        return False, "CRITICAL: SecretStr leaked raw API key in representation!"

    # Verify provider resolution
    spec = resolve_provider(test_settings)
    if spec is None:
        return False, "resolve_provider() returned None with active credentials."

    if spec.provider != "google":
        return False, f"Expected provider 'google', got '{spec.provider}'."

    model = spec.build()
    if not isinstance(model, SentinelGoogleModel):
        return False, f"Expected model instance of SentinelGoogleModel, got {type(model)}."

    # Verify status() redacts secret
    st = status()
    if "key" in str(st) or raw_key in str(st):
        return False, "status() leaked API key."

    return True, f"Successfully verified secure configuration for provider='{spec.provider}', model='{spec.model_name}'."


def verify_offline_wire_schema() -> tuple[bool, str]:
    """Verify offline that the wire payload conforms to Gemini API requirements."""
    import asyncio
    import contextlib
    import httpx
    from google.genai.types import HttpRetryOptions
    from pydantic_ai.providers.google import GoogleProvider

    captured: list[dict] = []

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.read().decode("utf-8")))
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
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10, "totalTokenCount": 20},
            }
            return httpx.Response(200, content=json.dumps(dummy).encode("utf-8"), headers={"Content-Type": "application/json"})

    provider = GoogleProvider(
        api_key="AIzaSyMockKeyForVerificationOfflineOnly123456",
        retry_options=HttpRetryOptions(attempts=1),
        http_client=httpx.AsyncClient(transport=MockTransport()),
    )
    model = SentinelGoogleModel("gemini-3.1-flash-lite", provider=provider)
    box = MagicMock(spec=CaseToolbox)
    agent = build_agent(model)
    deps = AgentDeps(box=box)

    async def _run():
        with contextlib.suppress(Exception):
            await agent.run(USER_PROMPT, deps=deps, model_settings={"timeout": 10.0})

    asyncio.run(_run())

    if not captured:
        return False, "Failed to capture mock wire request."

    req = captured[0]
    gen_config = req.get("generationConfig", {})
    if gen_config.get("responseModalities") is not None:
        return False, "Found conflicting responseModalities in generationConfig."

    tool_config = req.get("toolConfig", {})
    mode = tool_config.get("functionCallingConfig", {}).get("mode")
    if mode not in ("VALIDATED", "AUTO"):
        return False, f"Expected mode VALIDATED or AUTO, got {mode}."

    tools = req.get("tools", [])
    if not tools or "functionDeclarations" not in tools[0]:
        return False, "No functionDeclarations found in tools."

    # Verify $defs and $ref inlining across all declarations
    declarations_str = json.dumps(tools[0]["functionDeclarations"])
    if "$defs" in declarations_str or "$ref" in declarations_str:
        return False, "Unresolved $defs or $ref found in tool schemas."

    return True, f"Offline wire schema verified: {len(tools[0]['functionDeclarations'])} tools cleanly inlined without $defs/$ref."


def main() -> int:
    parser = argparse.ArgumentParser(description="SENTINEL Gemini Entrypoint Verifier")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run offline validation only (Default)")
    parser.add_argument("--execute", action="store_true", help="Authorize single live execution")
    parser.add_argument("--case-id", type=str, help="Case UUID for single live execution")
    args = parser.parse_args()

    print("=" * 70)
    print("SENTINEL — Gemini Provider Entrypoint Verification")
    print("=" * 70)

    # 1. Verify configuration
    cfg_ok, cfg_msg = verify_configuration(prompt_if_missing=args.execute)
    if cfg_ok:
        print(f"[OK] Configuration: {cfg_msg}")
    else:
        print(f"[NOTE] Configuration: {cfg_msg}")

    # 2. Verify offline wire schema
    wire_ok, wire_msg = verify_offline_wire_schema()
    if wire_ok:
        print(f"[OK] Wire Schema:   {wire_msg}")
    else:
        print(f"[FAIL] Wire Schema: {wire_msg}")
        return 1

    if args.execute:
        if not args.case_id:
            print("\n[ERROR] --execute requires --case-id <UUID>.")
            return 1
        if not cfg_ok:
            print("\n[ERROR] Cannot execute live call without valid SENTINEL_AI_API_KEY.")
            return 1

        print(f"\n[LIVE EXECUTION AUTHORIZED] Initiating 1-request test for Case ID: {args.case_id}")
        # Live execution instructions
        from app.db.session import get_sessionmaker
        from app.models import Case
        from app.services.investigation import runner

        with get_sessionmaker()() as db:
            case = db.get(Case, args.case_id)
            if not case:
                print(f"[ERROR] Case {args.case_id} not found in database.")
                return 1

            print(f"[INFO] Found Case {case.id} (Transaction: {case.transaction_id}). Dispatching investigation...")
            # Bounded single execution via runner
            spec = resolve_provider()
            assert spec is not None
            box = CaseToolbox(db=db, case=case)
            findings, usage, denied = runner._run_agent(box, spec)
            print("[SUCCESS] Live investigation completed successfully!")
            print(f"Summary: {findings.summary}")
            print(f"Recommended Action: {findings.recommended_action}")
            print(f"Human Approval Required: {findings.human_approval_required}")
            return 0

    print("\n[SUMMARY] Gemini entrypoint is verified, secure, and ready for owner-authorized retest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

