"""HTTP inbox forwarding worker. Never acknowledges an attempted request as acceptance."""

import argparse
import logging
import os
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.inbox_bridge import poll_once
from app.services.worker_health import heartbeat

__all__ = ["poll_once"]
log = logging.getLogger("sentinel.supabase_inbox")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    url = os.environ.get("SENTINEL_SUPABASE_URL", "")
    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "")
    api_url = os.environ.get(
        "SENTINEL_BRIDGE_API_URL", "http://127.0.0.1:" + os.environ.get("PORT", "8040")
    )
    parsed, api = urlparse(url), urlparse(api_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".supabase.co")
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or not key
    ):
        parser.error("Set a Supabase HTTPS project URL and service-role key securely")
    if (
        not api.hostname
        or api.username
        or api.password
        or api.path not in ("", "/")
        or api.query
        or api.fragment
        or (
            api.scheme != "https"
            and not (api.scheme == "http" and api.hostname in ("localhost", "127.0.0.1"))
        )
    ):
        parser.error("Bridge API URL must use HTTPS or loopback HTTP")
    settings = get_settings()
    if args.fixtures and not settings.allow_webhook_fixtures:
        parser.error("Fixture bridge requires the explicit non-production fixture configuration")
    configure_logging(settings.log_level)
    fixture_key = (
        settings.webhook_fixture_key.get_secret_value() if settings.webhook_fixture_key else None
    )
    name = "supabase_fixture_bridge" if args.fixtures else "supabase_bridge"
    failures = 0
    next_metrics = 0.0
    with (
        httpx.Client(
            base_url=url.rstrip("/") + "/rest/v1/rpc/",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=20,
            follow_redirects=False,
        ) as client,
        httpx.Client(
            base_url=api_url.rstrip("/"), timeout=30, follow_redirects=False
        ) as api_client,
    ):
        while True:
            try:
                count = poll_once(
                    client, api_client, fixtures=args.fixtures, fixture_key=fixture_key
                )
                snapshot: dict[str, object] | None = None
                if not args.fixtures and time.monotonic() >= next_metrics:
                    try:
                        metrics = client.post("sentinel_webhook_metrics", json={})
                        metrics.raise_for_status()
                        rows = metrics.json()
                        if not isinstance(rows, list):
                            raise ValueError("MetricsShape")
                        # Only retain known aggregate fields, never payloads/provider errors.
                        snapshot = {
                            "observed_at": datetime.now(UTC).isoformat(),
                            "groups": [
                                {
                                    k: row.get(k)
                                    for k in (
                                        "data_origin",
                                        "status",
                                        "count",
                                        "oldest_received_at",
                                        "last_attempt_at",
                                    )
                                }
                                for row in rows
                            ],
                        }
                    except Exception:
                        log.warning("inbox metrics unavailable")
                    next_metrics = time.monotonic() + 30
                heartbeat(name, "HEALTHY", processed=count, inbox_snapshot=snapshot)
                failures = 0
            except Exception as exc:
                failures += 1
                heartbeat(name, "DEGRADED", failure=type(exc).__name__)
                log.error("inbox poll failed", extra={"data": {"category": type(exc).__name__}})
                if args.once:
                    raise SystemExit(1) from None
            if args.once:
                return
            time.sleep(min(60, args.interval * 2 ** min(failures, 4)))


if __name__ == "__main__":
    main()
