#!/usr/bin/env python3
"""Fail-closed startup and readiness gate for SENTINEL API.

Ensures backend services are fully initialized, listening on the expected port,
passing both /health and /ready endpoints, and reporting compatible schema and
worker health before allowing downstream tests or workloads to execute.
Exits with code 0 on success; exits with nonzero code immediately on failure or timeout.
"""

import argparse
import logging
import socket
import sys
import time
from typing import Any
import urllib.error
import urllib.request
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("readiness_gate")


def check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


def http_get_json(url: str, timeout: float = 2.0) -> tuple[int, dict[str, Any] | None]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            content = resp.read()
            try:
                data = json.loads(content.decode("utf-8")) if content else None
            except json.JSONDecodeError:
                data = None
            return status, data
    except urllib.error.HTTPError as e:
        content = e.read()
        try:
            data = json.loads(content.decode("utf-8")) if content else None
        except json.JSONDecodeError:
            data = None
        return e.code, data
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError):
        return 0, None


def wait_until_ready(
    host: str = "127.0.0.1",
    port: int = 8000,
    timeout_seconds: float = 30.0,
    interval_seconds: float = 0.5,
    expected_revision: str | None = None,
    require_workers: bool = False,
) -> bool:
    start_time = time.monotonic()
    deadline = start_time + timeout_seconds

    base_url = f"http://{host}:{port}"
    health_url = f"{base_url}/api/v1/health"
    ready_url = f"{base_url}/api/v1/ready"

    log.info(f"Initiating fail-closed readiness probe for {base_url} (timeout={timeout_seconds}s)")

    # Phase 1: Wait for TCP port connection
    port_open = False
    while time.monotonic() < deadline:
        if check_tcp_port(host, port, timeout=1.0):
            port_open = True
            log.info(f"Port {port} is open and accepting TCP connections.")
            break
        time.sleep(interval_seconds)

    if not port_open:
        log.error(f"FAIL-CLOSED: Port {port} did not open within {timeout_seconds}s.")
        return False

    # Phase 2: Wait for /api/v1/health returning 200 {"status": "ok"}
    health_ok = False
    while time.monotonic() < deadline:
        status, data = http_get_json(health_url, timeout=2.0)
        if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
            health_ok = True
            log.info(f"Health check /api/v1/health passed (HTTP 200).")
            break
        time.sleep(interval_seconds)

    if not health_ok:
        log.error(f"FAIL-CLOSED: /api/v1/health did not return 200 OK within {timeout_seconds}s.")
        return False

    # Phase 3: Wait for /api/v1/ready returning 200 {"status": "ready"}
    while time.monotonic() < deadline:
        status, data = http_get_json(ready_url, timeout=2.0)
        if status == 200 and isinstance(data, dict):
            status_field = data.get("status")
            checks = data.get("checks", {})
            if status_field == "ready" and checks.get("database") == "ok" and checks.get("schema") == "ok":
                # Check expected schema revision if specified
                if expected_revision and checks.get("migration") != expected_revision:
                    log.error(
                        f"FAIL-CLOSED: Migration revision mismatch: expected {expected_revision}, "
                        f"got {checks.get('migration')}"
                    )
                    return False

                # Check workers if required
                if require_workers:
                    for w in ("pipeline", "supabase_bridge"):
                        if checks.get(w) != "ok":
                            log.warning(f"Worker {w} not ready yet ({checks.get(w)}); retrying...")
                            break
                    else:
                        log.info(f"Readiness check /api/v1/ready passed with all required workers.")
                        return True
                else:
                    log.info(f"Readiness check /api/v1/ready passed (HTTP 200).")
                    return True
        elif status == 503:
            log.warning(f"Backend reported 503 Not Ready: {data}; retrying...")
        time.sleep(interval_seconds)

    log.error(f"FAIL-CLOSED: /api/v1/ready timed out after {timeout_seconds}s.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for SENTINEL API readiness (fail-closed)")
    parser.add_argument("--host", default="127.0.0.1", help="API host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="API port (default: 8000)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds (default: 30)")
    parser.add_argument("--interval", type=float, default=0.5, help="Poll interval in seconds (default: 0.5)")
    parser.add_argument("--expected-revision", default=None, help="Expected Alembic migration head")
    parser.add_argument("--require-workers", action="store_true", help="Require pipeline and bridge workers")

    args = parser.parse_args()
    success = wait_until_ready(
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout,
        interval_seconds=args.interval,
        expected_revision=args.expected_revision,
        require_workers=args.require_workers,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

