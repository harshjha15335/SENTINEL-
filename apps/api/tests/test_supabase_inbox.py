import json
import uuid

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PaymentEvent
from app.models.enums import TransactionStatus
from app.services.webhooks import SignatureVerifier
from app.workers.supabase_inbox import poll_once
from tests.test_webhooks import (
    WEBHOOK_ID,
    _sandbox_txn,
    capture_resource,
    event_body,
    keypair,
    sign,
)

__all__ = ["keypair"]


@pytest.fixture(autouse=True)
def clear_settings_cache():  # type: ignore[no-untyped-def]
    yield
    get_settings.cache_clear()


def setup_delivery(monkeypatch, keypair, resource=None):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SENTINEL_PAYPAL_WEBHOOK_ID", WEBHOOK_ID)
    get_settings.cache_clear()
    key, pem = keypair
    raw = event_body("WH-SUPABASE-1", "PAYMENT.CAPTURE.COMPLETED", resource or {"id": "UNMATCHED"})
    signed = sign(key, raw, WEBHOOK_ID)
    row = {
        "id": str(uuid.uuid4()),
        "lease_token": str(uuid.uuid4()),
        "provider_event_id": "WH-SUPABASE-1",
        "raw_body": raw.decode(),
        "signature_headers": {
            "paypal-transmission-id": signed.transmission_id,
            "paypal-transmission-time": signed.transmission_time,
            "paypal-cert-url": signed.cert_url,
            "paypal-auth-algo": signed.auth_algo,
            "paypal-transmission-sig": signed.transmission_sig,
        },
    }
    return row, SignatureVerifier(fetch=lambda _: pem)


def test_signed_inbox_commits_before_ack_and_duplicate_is_safe(
    db: Session,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
    keypair,  # type: ignore[no-untyped-def]
) -> None:
    txn = _sandbox_txn(db, tenant)
    row, verifier = setup_delivery(
        monkeypatch, keypair, capture_resource("CAPTURE-SUPABASE", txn.paypal_order_id)
    )
    acknowledgements = []

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("sentinel_claim_webhooks"):
            return httpx.Response(200, json=[row])
        body = json.loads(request.content)
        assert body["p_success"] is True
        # Separate session observes the durable commit before we acknowledge Supabase.
        assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
        acknowledgements.append(body)
        return httpx.Response(200, json=True)

    with httpx.Client(
        base_url="https://example.supabase.co/rest/v1/rpc/",
        transport=httpx.MockTransport(transport),
    ) as client:
        assert poll_once(client, verifier) == 1
        assert poll_once(client, verifier) == 1
    assert len(acknowledgements) == 2
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
    db.refresh(txn)
    assert txn.status is TransactionStatus.CAPTURED
    assert txn.paypal_capture_id == "CAPTURE-SUPABASE"


def test_tampered_inbox_is_rejected_without_local_event(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    keypair,  # type: ignore[no-untyped-def]
) -> None:
    row, verifier = setup_delivery(monkeypatch, keypair)
    row["raw_body"] += " "

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("sentinel_claim_webhooks"):
            return httpx.Response(200, json=[row])
        assert json.loads(request.content)["p_success"] is False
        return httpx.Response(200, json=True)

    with httpx.Client(
        base_url="https://example.supabase.co/rest/v1/rpc/",
        transport=httpx.MockTransport(transport),
    ) as client:
        assert poll_once(client, verifier) == 0
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 0


def test_lost_ack_can_retry_without_duplicate_local_event(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    keypair,  # type: ignore[no-untyped-def]
) -> None:
    row, verifier = setup_delivery(monkeypatch, keypair)
    failed = False

    def transport(request: httpx.Request) -> httpx.Response:
        nonlocal failed
        if request.url.path.endswith("sentinel_claim_webhooks"):
            return httpx.Response(200, json=[row])
        if not failed:
            failed = True
            raise httpx.ReadTimeout("lost acknowledgement")
        return httpx.Response(200, json=True)

    with httpx.Client(
        base_url="https://example.supabase.co/rest/v1/rpc/",
        transport=httpx.MockTransport(transport),
    ) as client:
        with pytest.raises(httpx.ReadTimeout):
            poll_once(client, verifier)
        assert poll_once(client, verifier) == 1
    assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 1
