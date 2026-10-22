"""Supervise API, event/scoring worker and optional Supabase bridge in one container."""

import os
import signal
import subprocess
import sys
import time

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if settings.hosted_deployment and "*" in os.environ.get("SENTINEL_FORWARDED_ALLOW_IPS", ""):
        raise SystemExit("Hosted deployment requires explicit trusted proxy addresses")
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
            os.environ.get("SENTINEL_FORWARDED_ALLOW_IPS", "127.0.0.1"),
        ],
        [sys.executable, "-m", "app.workers.pipeline"],
    ]
    if os.environ.get("SENTINEL_SUPABASE_URL"):
        commands.append([sys.executable, "-m", "app.workers.supabase_inbox"])
    children: list[subprocess.Popen[bytes]] = []
    stopping = False

    def stop(_signal: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    failures = [0 for _ in commands]
    try:
        children = [subprocess.Popen(command) for command in commands]  # noqa: S603
        while not stopping:
            for i, child in enumerate(children):
                if child.poll() is not None:
                    failures[i] += 1
                    if failures[i] >= 5:
                        raise SystemExit("Worker restart budget exhausted")
                    time.sleep(min(5, failures[i]))
                    if not stopping:
                        children[i] = subprocess.Popen(commands[i])  # noqa: S603
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
