import base64
import json
import zlib
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import PaymentEvent, Transaction
from app.models.enums import (
    DataOrigin,
    EventProcessing,
    EventVerification,
    TransactionStatus,
)
from app.services.paypal.types import WebhookHeaders
from app.services.webhooks import (
    SignatureVerifier,
    WebhookVerificationError,
    classify_verification,
    process_event,
    store_event,
)
from tests.conftest import Tenant

CERT_URL = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-360caa42-test"
WEBHOOK_ID = "8PT597110X687430LKGECATA"


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "messageverificationcerts.sandbox.paypal.com")]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return key, cert.public_bytes(serialization.Encoding.PEM)


def sign(key, body: bytes, webhook_id: str, tid: str = "tx-1") -> WebhookHeaders:
    ts = "2026-10-10T12:00:00Z"
    msg = f"{tid}|{ts}|{webhook_id}|{zlib.crc32(body) & 0xFFFFFFFF}".encode()
    sig = base64.b64encode(key.sign(msg, padding.PKCS1v15(), hashes.SHA256())).decode()
    return WebhookHeaders(tid, ts, CERT_URL, "SHA256withRSA", sig)


def event_body(event_id: str, etype: str, resource: dict) -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "event_type": etype,
            "create_time": "2026-10-10T12:00:01Z",
            "resource": resource,
        },
        separators=(",", ":"),
    ).encode()


def capture_resource(capture_id: str, order_id: str) -> dict:
    return {
        "id": capture_id,
        "status": "COMPLETED",
        "amount": {"currency_code": "USD", "value": "25.00"},
        "supplementary_data": {"related_ids": {"order_id": order_id}},
    }


@pytest.fixture
def verifier(keypair):
    _, pem = keypair
    return SignatureVerifier(fetch=lambda url: pem)


def test_valid_signature_is_verified(keypair, verifier) -> None:
    key, _ = keypair
    body = event_body("WH-1", "PAYMENT.CAPTURE.COMPLETED", {})
    result = classify_verification(
        verifier, sign(key, body, WEBHOOK_ID), body, WEBHOOK_ID, accept_simulator=False
    )
    assert result is EventVerification.VERIFIED


def test_tampered_body_is_rejected(keypair, verifier) -> None:
    key, _ = keypair
    body = event_body("WH-1", "PAYMENT.CAPTURE.COMPLETED", {})
    headers = sign(key, body, WEBHOOK_ID)
    tampered = body.replace(b"WH-1", b"WH-2")
    with pytest.raises(WebhookVerificationError):
        classify_verification(verifier, headers, tampered, WEBHOOK_ID, accept_simulator=False)


def test_reformatted_json_fails_because_raw_bytes_matter(keypair, verifier) -> None:
    key, _ = keypair
    body = event_body("WH-1", "PAYMENT.CAPTURE.COMPLETED", {})
    headers = sign(key, body, WEBHOOK_ID)
    pretty = json.dumps(json.loads(body), indent=2).encode()
    with pytest.raises(WebhookVerificationError):
        classify_verification(verifier, headers, pretty, WEBHOOK_ID, accept_simulator=False)


def test_simulator_events_are_fixture_not_verified(keypair, verifier) -> None:
    key, _ = keypair
    body = event_body("WH-SIM", "PAYMENT.CAPTURE.COMPLETED", {})
    headers = sign(key, body, "WEBHOOK_ID")
    assert (
        classify_verification(verifier, headers, body, WEBHOOK_ID, accept_simulator=True)
        is EventVerification.FIXTURE
    )
    with pytest.raises(WebhookVerificationError):
        classify_verification(verifier, headers, body, WEBHOOK_ID, accept_simulator=False)


def test_non_paypal_cert_host_rejected(keypair, verifier) -> None:
    key, _ = keypair
    body = event_body("WH-1", "X", {})
    h = sign(key, body, WEBHOOK_ID)
    evil = WebhookHeaders(
        h.transmission_id,
        h.transmission_time,
        "https://evil.example/cert.pem",
        h.auth_algo,
        h.transmission_sig,
    )
    with pytest.raises(WebhookVerificationError):
        classify_verification(verifier, evil, body, WEBHOOK_ID, accept_simulator=False)


def _sandbox_txn(db, tenant: Tenant, order_id: str = "5O0000000000001") -> Transaction:
    txn = Transaction(
        merchant_id=tenant.merchant.id,
        product_id=tenant.product.id,
        quantity=1,
        paypal_order_id=order_id,
        amount_minor=2500,
        currency="USD",
        status=TransactionStatus.ORDER_CREATED,
        create_idempotency_key="k-" + order_id,
        paypal_request_id="r-" + order_id,
        data_origin=DataOrigin.LIVE_SANDBOX,
        provider_summary={},
    )
    db.add(txn)
    db.commit()
    return txn


def test_duplicate_delivery_is_idempotent(db, tenant: Tenant) -> None:
    _sandbox_txn(db, tenant)
    body = event_body(
        "WH-DUP", "PAYMENT.CAPTURE.COMPLETED", capture_resource("CAP1", "5O0000000000001")
    )
    e1, created1 = store_event(db, body, EventVerification.VERIFIED, "t1")
    e2, created2 = store_event(db, body, EventVerification.VERIFIED, "t2")
    assert created1 and not created2
    assert e1.id == e2.id
    db.refresh(e1)
    assert e1.delivery_count == 2
    assert db.scalars(select(PaymentEvent)).all().__len__() == 1


def test_capture_event_reconciles_transaction(db, tenant: Tenant) -> None:
    txn = _sandbox_txn(db, tenant)
    body = event_body(
        "WH-C", "PAYMENT.CAPTURE.COMPLETED", capture_resource("CAP1", "5O0000000000001")
    )
    event, _ = store_event(db, body, EventVerification.VERIFIED, "t")
    event = process_event(db, event.id)
    db.refresh(txn)
    assert event.processing_status is EventProcessing.PROCESSED
    assert txn.status is TransactionStatus.CAPTURED
    assert txn.paypal_capture_id == "CAP1"


def test_out_of_order_events_do_not_regress(db, tenant: Tenant) -> None:
    txn = _sandbox_txn(db, tenant)
    txn.paypal_capture_id = "CAP1"
    txn.status = TransactionStatus.CAPTURED
    db.commit()
    refund = {
        "id": "REF1",
        "status": "COMPLETED",
        "links": [
            {"rel": "up", "href": "https://api.sandbox.paypal.com/v2/payments/captures/CAP1"}
        ],
        "seller_payable_breakdown": {
            "total_refunded_amount": {"currency_code": "USD", "value": "25.00"}
        },
    }
    e1, _ = store_event(
        db, event_body("WH-R", "PAYMENT.CAPTURE.REFUNDED", refund), EventVerification.VERIFIED, "a"
    )
    process_event(db, e1.id)
    late = event_body(
        "WH-P", "PAYMENT.CAPTURE.PENDING", capture_resource("CAP1", "5O0000000000001")
    )
    e2, _ = store_event(db, late, EventVerification.VERIFIED, "b")
    process_event(db, e2.id)
    db.refresh(txn)
    assert txn.status is TransactionStatus.REFUNDED


def test_partial_refund(db, tenant: Tenant) -> None:
    txn = _sandbox_txn(db, tenant)
    txn.paypal_capture_id = "CAP1"
    txn.status = TransactionStatus.CAPTURED
    db.commit()
    refund = {
        "id": "REF1",
        "links": [
            {"rel": "up", "href": "https://api.sandbox.paypal.com/v2/payments/captures/CAP1"}
        ],
        "seller_payable_breakdown": {
            "total_refunded_amount": {"currency_code": "USD", "value": "10.00"}
        },
    }
    e, _ = store_event(
        db, event_body("WH-PR", "PAYMENT.CAPTURE.REFUNDED", refund), EventVerification.VERIFIED, "a"
    )
    process_event(db, e.id)
    db.refresh(txn)
    assert txn.status is TransactionStatus.PARTIALLY_REFUNDED


def test_simulator_event_never_mutates_sandbox_records(db, tenant: Tenant) -> None:
    txn = _sandbox_txn(db, tenant)
    body = event_body(
        "WH-S", "PAYMENT.CAPTURE.COMPLETED", capture_resource("CAP1", "5O0000000000001")
    )
    e, _ = store_event(db, body, EventVerification.FIXTURE, "t")
    e = process_event(db, e.id)
    db.refresh(txn)
    assert e.processing_status is EventProcessing.IGNORED
    assert e.data_origin is DataOrigin.SIMULATED
    assert txn.status is TransactionStatus.ORDER_CREATED


def test_unknown_resource_is_ignored_with_reason(db) -> None:
    body = event_body("WH-U", "PAYMENT.CAPTURE.COMPLETED", capture_resource("NOPE", "NOPE"))
    e, _ = store_event(db, body, EventVerification.VERIFIED, "t")
    e = process_event(db, e.id)
    assert e.processing_status is EventProcessing.IGNORED
    assert "No matching" in (e.error_reason or "")


def test_endpoint_persists_then_acknowledges(
    app_client: TestClient, keypair, verifier, db, tenant, monkeypatch
) -> None:
    from app.api.v1.webhooks import get_verifier
    from app.core.config import get_settings
    from app.main import app

    monkeypatch.setattr(get_settings(), "paypal_webhook_id", WEBHOOK_ID)
    app.dependency_overrides[get_verifier] = lambda: verifier
    txn = _sandbox_txn(db, tenant)
    key, _ = keypair
    body = event_body(
        "WH-E2E", "PAYMENT.CAPTURE.COMPLETED", capture_resource("CAP9", txn.paypal_order_id)
    )
    h = sign(key, body, WEBHOOK_ID)
    headers = {
        "paypal-transmission-id": h.transmission_id,
        "paypal-transmission-time": h.transmission_time,
        "paypal-cert-url": h.cert_url,
        "paypal-auth-algo": h.auth_algo,
        "paypal-transmission-sig": h.transmission_sig,
        "content-type": "application/json",
    }
    first = app_client.post("/api/v1/webhooks/paypal", content=body, headers=headers)
    second = app_client.post("/api/v1/webhooks/paypal", content=body, headers=headers)
    assert first.json() == {"received": True, "duplicate": False}
    assert second.json() == {"received": True, "duplicate": True}
    db.expire_all()
    db.refresh(txn)
    assert txn.status is TransactionStatus.CAPTURED  # processed by the background task
    bad = app_client.post("/api/v1/webhooks/paypal", content=body + b" ", headers=headers)
    assert bad.status_code == 400
    missing = app_client.post("/api/v1/webhooks/paypal", content=body)
    assert missing.status_code == 400
