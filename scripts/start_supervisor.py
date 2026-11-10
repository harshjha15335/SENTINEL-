"""SENTINEL — Secure Multi-Worker Supervisor Runner.

Starts FastAPI (Uvicorn), the Event/Scoring Pipeline worker, and the Supabase Inbox Bridge.
Obtains the Supabase service_role key strictly in memory via getpass (never persisted to disk or registry).

Usage:
    python scripts/start_supervisor.py
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


def main() -> None:
    print("=" * 70)
    print("SENTINEL — Secure Multi-Worker Supervisor")
    print("=" * 70)

    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not key:
        print("[SECURE PROMPT] SENTINEL_SUPABASE_SERVICE_ROLE_KEY not detected in process memory.")
        print("Input is masked and handled strictly in RAM (zero disk/registry persistence).\n")
        try:
            key = getpass.getpass("Enter Supabase service_role Key: ").strip()
        except (KeyboardInterrupt, EOFError):
            sys.exit("\n[ABORT] Supervisor startup cancelled.")

    if not key:
        sys.exit("[FAIL] Supabase service_role key is required to start the inbox bridge.")

    # Validate key against Supabase RPC
    print("\n[Step 1/2] Verifying Supabase Service Role Authentication...")
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

    # Pre-check port and locks to avoid conflicting processes
    port = int(os.environ.get("PORT", "8040"))
    host = os.environ.get("HOST", "127.0.0.1")
    fastapi_already_running = False
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.get(f"http://{host}:{port}/api/v1/health")
            if r.status_code == 200:
                fastapi_already_running = True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass

    if fastapi_already_running:
        print(f"\n[NOTICE] FastAPI server is ALREADY running on http://{host}:{port}.")
        print("Starting another supervisor would create duplicate processes or port conflicts.")
        print("To launch the bridge worker alongside the existing services, execute:")
        print("    python scripts/start_bridge.py")
        print("\nIf you wish to restart all services under a single supervisor, terminate the existing")
        print("standalone processes first.")
        sys.exit(0)
    os.environ["SENTINEL_SUPABASE_URL"] = PROJECT_URL
    os.environ["SENTINEL_SUPABASE_SERVICE_ROLE_KEY"] = key
    os.environ["PORT"] = os.environ.get("PORT", "8040")
    os.environ["HOST"] = os.environ.get("HOST", "127.0.0.1")
    os.environ["SENTINEL_BRIDGE_API_URL"] = f"http://{os.environ['HOST']}:{os.environ['PORT']}"

    print(f"  - Target Host:            {os.environ['HOST']}:{os.environ['PORT']}")
    print(f"  - In-Memory Supabase Key: CONFIGURED (length: {len(key)})")
    print("  - Spawning: uvicorn (FastAPI), pipeline worker, and supabase_inbox worker...")
    print("=" * 70)
    print("Supervisor is running. Press [Ctrl+C] to gracefully terminate all workers.\n")

    from app.workers.supervisor import main as supervisor_main

    supervisor_main()


if __name__ == "__main__":
    main()

