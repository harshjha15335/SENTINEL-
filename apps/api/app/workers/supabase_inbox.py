"""Bridge a private Supabase inbox into SENTINEL's existing verified-event processor.

Run `python -m app.workers.supabase_inbox [--once]`. The Edge Function verifies with
PayPal before enqueueing; this bridge independently verifies the original raw bytes.
Local commits precede remote acknowledgement, making lost acknowledgements safe to retry.
"""

import argparse
import json
import logging
import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.models.enums import EventProcessing, EventVerification
from app.services.webhooks import SignatureVerifier, parse_headers, process_event, store_event

log = logging.getLogger("sentinel.supabase_inbox")


def poll_once(client: httpx.Client, verifier: SignatureVerifier | None = None) -> int:
    webhook_id = get_settings().paypal_webhook_id
    if not webhook_id or webhook_id == "WEBHOOK_ID":
        raise ValueError("Configure SENTINEL_PAYPAL_WEBHOOK_ID before draining the inbox")
    verifier = verifier or SignatureVerifier()
    claimed = client.post("sentinel_claim_webhooks", json={"p_limit": 25})
    claimed.raise_for_status()
    rows: list[dict[str, Any]] = claimed.json()
    processed = 0
    for row in rows:
        success, category = False, None
        try:
            raw = row["raw_body"].encode("utf-8")
            headers = parse_headers(row["signature_headers"].get)
            verifier.verify(headers, raw, webhook_id)
            if json.loads(raw).get("id") != row["provider_event_id"]:
                raise ValueError("Inbox event id does not match the verified body")
            with get_sessionmaker()() as db:
                event, _created = store_event(
                    db, raw, EventVerification.VERIFIED, headers.transmission_id
                )
                event = process_event(db, event.id)
                if event.processing_status is EventProcessing.FAILED:
                    raise RuntimeError("Local event processing failed")
            success = True
        except Exception as exc:
            # Categories only: no provider error body, raw event, key or signed URL in logs.
            category = type(exc).__name__
            log.warning("inbox delivery failed", extra={"data": {"category": category}})
        completed = client.post(
            "sentinel_finish_webhook",
            json={
                "p_id": row["id"],
                "p_lease_token": row["lease_token"],
                "p_success": success,
                "p_error": category,
            },
        )
        completed.raise_for_status()
        if completed.json() is not True:
            raise RuntimeError("Inbox lease expired or was replaced; delivery will retry")
        processed += int(success)
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be positive")
    url = os.environ.get("SENTINEL_SUPABASE_URL", "")
    key = os.environ.get("SENTINEL_SUPABASE_SERVICE_ROLE_KEY", "")
    parsed = urlparse(url)
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
        parser.error(
            "Set a Supabase HTTPS project URL and service-role key in environment settings"
        )
    configure_logging(get_settings().log_level)
    with httpx.Client(
        base_url=url.rstrip("/") + "/rest/v1/rpc/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=20,
        follow_redirects=False,
    ) as client:
        verifier = SignatureVerifier()
        while True:
            try:
                count = poll_once(client, verifier)
                if count:
                    log.info("inbox processed", extra={"data": {"count": count}})
            except Exception as exc:
                log.error("inbox poll failed", extra={"data": {"category": type(exc).__name__}})
                if args.once:
                    raise SystemExit(1) from None
            if args.once:
                return
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
