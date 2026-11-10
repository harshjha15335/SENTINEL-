"""SENTINEL — Secure Supabase Inbox Bridge Worker Runner.

Connects to the already running FastAPI instance (port 8040) and starts the Supabase
Inbox Bridge. Prompts securely for the Supabase service_role key via getpass
(in-memory only; zero disk/registry persistence).

Usage:
    python scripts/start_bridge.py
"""

import getpass
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

PROJECT_URL = "https://cfslzvvdjxstpupkqbpw.supabase.co"
TARGET_API = os.environ.get("SENTINEL_BRIDGE_API_URL", "http://127.0.0.1:8040")


def main() -> None:
    print("=" * 70)
    print("SENTINEL — Secure Supabase Inbox Bridge Worker")
    print("=" * 70)

    # 1. Verify FastAPI server on loopback
    print(f"\n[Step 1/3] Verifying FastAPI Server at {TARGET_API}...")
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{TARGET_API.rstrip('/')}/api/v1/health")
            if resp.status_code == 200:
                print("  - FastAPI Health Check:   HTTP 200 (Active)")
            else:
                sys.exit(f"  [FAIL] FastAPI returned unexpected status: {resp.status_code}")
    except (httpx.ConnectError, httpx.TimeoutException):
        sys.exit(f"  [FAIL] Cannot connect to FastAPI at {TARGET_API}. Is the server running?")

    # 2. Obtain Supabase service_role key
    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        print("\n[Step 2/3] Supabase Authentication Key...")
        print("[SECURE PROMPT] SENTINEL_SUPABASE_SERVICE_ROLE_KEY not detected in process memory.")
        print("Input is masked and handled strictly in RAM (zero disk/registry persistence).\n")
        try:
            key = getpass.getpass("Enter Supabase service_role Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit("\n[ABORT] Entry cancelled.")

    if not key:
        sys.exit("[FAIL] Supabase service_role key is required to start the bridge.")

    # 3. Test Supabase PostgREST RPC
    print("\n[Step 3/3] Authenticating PostgREST RPC with Supabase...")
    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.post(
                f"{PROJECT_URL}/rest/v1/rpc/sentinel_webhook_metrics",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                json={},
            )
            if resp.status_code == 200:
                print("  - Supabase PostgREST RPC: AUTHENTICATED (HTTP 200)")
            else:
                sys.exit(f"  [FAIL] Supabase RPC returned HTTP {resp.status_code}: {resp.text}")
        except httpx.HTTPError as exc:
            sys.exit(f"  [FAIL] Network error connecting to Supabase: {exc}")

    # Set in-memory environment variables and launch
    os.environ["SENTINEL_SUPABASE_URL"] = PROJECT_URL
    os.environ["SENTINEL_SUPABASE_SERVICE_ROLE_KEY"] = key
    os.environ["SENTINEL_BRIDGE_API_URL"] = TARGET_API

    print("=" * 70)
    print("Supabase Inbox Bridge is active and polling. Emitting heartbeats to PostgreSQL.")
    print("Press [Ctrl+C] to stop.\n")

    from app.workers.supabase_inbox import main as bridge_main

    bridge_main()


if __name__ == "__main__":
    main()

