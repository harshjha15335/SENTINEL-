"""Supervise API, event/scoring worker and optional Supabase bridge in one container."""

import os
import signal
import subprocess
import sys
import time
from ipaddress import IPv4Network, IPv6Network, collapse_addresses, ip_network
from pathlib import Path

from app.core.config import get_settings
from app.services.worker_health import heartbeat


def forwarded_allow_ips(value: str, *, hosted: bool) -> str:
    if not hosted:
        return value or "127.0.0.1"
    try:
        if not value.strip():
            raise ValueError("Missing trusted proxy scope")
        networks = [ip_network(part.strip(), strict=False) for part in value.split(",")]
        v4 = list(collapse_addresses(n for n in networks if isinstance(n, IPv4Network)))
        v6 = list(collapse_addresses(n for n in networks if isinstance(n, IPv6Network)))
        if any(network.prefixlen == 0 for network in v4) or any(
            network.prefixlen == 0 for network in v6
        ):
            raise ValueError("Unrestricted proxy scope")
    except ValueError as exc:
        raise SystemExit("Hosted deployment requires explicit bounded proxy IPs or CIDRs") from exc
    return ",".join(part.strip() for part in value.split(","))


def main() -> None:
    settings = get_settings()
    proxies = forwarded_allow_ips(
        os.environ.get("SENTINEL_FORWARDED_ALLOW_IPS", ""), hosted=settings.hosted_deployment
    )
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            os.environ.get("HOST", "127.0.0.1"),
            "--port",
            os.environ.get("PORT", "8040"),
            "--proxy-headers",
            "--forwarded-allow-ips",
            proxies,
        ],
        [sys.executable, "-m", "app.workers.pipeline"],
    ]
    if settings.require_workers_ready and not settings.worker_configuration_ready:
        raise SystemExit("Required Supabase integration is not configured")
    if settings.supabase_configured:
        heartbeat("supabase_bridge", "STARTING")
        commands.append([sys.executable, "-m", "app.workers.supabase_inbox"])
    children: list[subprocess.Popen[bytes]] = []
    stopping = False

    def stop(_signal: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    failures = [0 for _ in commands]
    api_dir = str(Path(__file__).resolve().parents[2])
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{api_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = api_dir
    try:
        children = [subprocess.Popen(command, cwd=api_dir, env=env) for command in commands]  # noqa: S603
        while not stopping:
            for i, child in enumerate(children):
                if child.poll() is not None:
                    if i:
                        heartbeat(
                            "pipeline" if i == 1 else "supabase_bridge",
                            "DEGRADED",
                            failure="ProcessExited",
                        )
                    failures[i] += 1
                    if failures[i] >= 5:
                        raise SystemExit("Worker restart budget exhausted")
                    time.sleep(min(5, failures[i]))
                    if not stopping:
                        children[i] = subprocess.Popen(commands[i], cwd=api_dir, env=env)  # noqa: S603
            time.sleep(1)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    main()
