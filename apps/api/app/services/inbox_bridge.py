"""Forward exact signed bytes to FastAPI; acknowledge only a matching durable receipt."""

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

log = logging.getLogger("sentinel.inbox_bridge")


class InboxMismatch(Exception):
    pass


class DeliveryDeferred(Exception):
    pass


PAYPAL_HEADERS = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-cert-url",
    "paypal-auth-algo",
    "paypal-transmission-sig",
)


def poll_once(
    client: httpx.Client,
    api_client: httpx.Client,
    *,
    fixtures: bool = False,
    fixture_key: str | None = None,
) -> int:
    origin = "SIMULATED" if fixtures else "LIVE_SANDBOX"
    claimed = client.post("sentinel_claim_webhooks", json={"p_limit": 1, "p_origin": origin})
    claimed.raise_for_status()
    processed = 0
    for row in claimed.json():
        identity = {"p_id": row["id"], "p_lease_token": row["lease_token"]}
        renewed = client.post("sentinel_renew_webhook", json=identity)
        renewed.raise_for_status()
        if renewed.json() is not True:
            log.warning("inbox lease lost before forwarding")
            continue
        success, category = False, None
        trace_id = hashlib.sha256(str(row["provider_event_id"]).encode()).hexdigest()[:32]
        try:
            raw = row["raw_body"].encode("utf-8")
            try:
                payload = json.loads(raw)
            except ValueError as exc:
                raise InboxMismatch from exc
            if (
                not isinstance(payload, dict)
                or payload.get("id") != row["provider_event_id"]
                or row["data_origin"] != origin
            ):
                raise InboxMismatch
            headers = {
                name: row["signature_headers"][name]
                for name in PAYPAL_HEADERS
                if name in row["signature_headers"]
            }
            headers["content-type"] = "application/json"
            headers["x-correlation-id"] = trace_id
            path = "/api/v1/webhooks/paypal"
            if fixtures:
                if not fixture_key or not str(payload["id"]).startswith("FIXTURE-"):
                    raise InboxMismatch
                headers["x-sentinel-fixture-signature"] = hmac.new(
                    fixture_key.encode(), raw, hashlib.sha256
                ).hexdigest()
                path = "/api/v1/webhooks/fixtures/paypal"
            response = api_client.post(path, content=raw, headers=headers)
            if response.status_code in (400, 403, 404, 413, 422):
                category = "PERMANENT_HTTP_" + str(response.status_code)
            else:
                response.raise_for_status()
                receipt: dict[str, Any] = response.json()
                expected = {
                    "received": True,
                    "durable": True,
                    "event_id": payload["id"],
                    "payload_sha256": hashlib.sha256(raw).hexdigest(),
                    "data_origin": origin,
                    "verification_status": "FIXTURE" if fixtures else "VERIFIED",
                }
                if any(receipt.get(k) != v for k, v in expected.items()):
                    raise RuntimeError("ReceiptMismatch")
                success = True
        except InboxMismatch:
            category = "PERMANENT_InboxMismatch"
        except Exception as exc:
            category = "RETRY_" + type(exc).__name__
        completed = client.post(
            "sentinel_finish_webhook",
            json={
                **identity,
                "p_success": success,
                "p_error": category,
            },
        )
        completed.raise_for_status()
        if completed.json() is not True:
            raise RuntimeError("LeaseReplaced")
        processed += int(success)
        log.info(
            "inbox forward",
            extra={
                "data": {
                    "origin": origin,
                    "accepted": success,
                    "category": category,
                    "event_trace_id": trace_id,
                }
            },
        )
        if category and category.startswith("RETRY_"):
            raise DeliveryDeferred(category)
    return processed
