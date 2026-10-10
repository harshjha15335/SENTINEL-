"""PayPal webhook intake: verify, persist, then process durably and idempotently.

Verification follows PayPal's documented self-verification:
  message = f"{transmission_id}|{transmission_time}|{webhook_id}|{crc32(raw_body)}"
  RSA-SHA256 signature (base64 in PAYPAL-TRANSMISSION-SIG) checked with the public key of the
  certificate at PAYPAL-CERT-URL. The certificate is only fetched from PayPal hosts over HTTPS.
This is not a shared-secret HMAC. Simulator ("mock") events are signed with the literal
webhook id ``WEBHOOK_ID`` and are recorded as FIXTURE, never as verified app events.
"""

import base64
import hashlib
import json
import logging
import threading
import zlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PaymentEvent, RawPayload, Transaction
from app.models.enums import (
    DataOrigin,
    EventProcessing,
    EventVerification,
    TransactionStatus,
)
from app.services import audit
from app.services.paypal.types import Money, WebhookHeaders

log = logging.getLogger("sentinel.webhooks")

SIMULATOR_WEBHOOK_ID = "WEBHOOK_ID"
_ALLOWED_CERT_HOSTS = {
    "api.paypal.com",
    "api.sandbox.paypal.com",
    "api-m.paypal.com",
    "api-m.sandbox.paypal.com",
}
MAX_PROCESSING_ATTEMPTS = 5


class WebhookVerificationError(Exception):
    pass


CertFetcher = Callable[[str], bytes]


def _default_fetch(url: str) -> bytes:
    resp = httpx.get(url, timeout=10.0, follow_redirects=False)
    resp.raise_for_status()
    return resp.content


class SignatureVerifier:
    def __init__(self, fetch: CertFetcher = _default_fetch) -> None:
        self._fetch = fetch
        self._cache: dict[str, x509.Certificate] = {}
        self._lock = threading.Lock()

    def _certificate(self, url: str) -> x509.Certificate:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_CERT_HOSTS:
            raise WebhookVerificationError("Certificate URL is not a PayPal HTTPS host")
        with self._lock:
            cert = self._cache.get(url)
        if cert is None:
            try:
                cert = x509.load_pem_x509_certificate(self._fetch(url))
            except Exception as exc:
                raise WebhookVerificationError(
                    f"Could not load certificate: {type(exc).__name__}"
                ) from exc
            with self._lock:
                self._cache[url] = cert
        now = datetime.now(UTC)
        if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
            raise WebhookVerificationError("Certificate is outside its validity period")
        return cert

    def verify(self, headers: WebhookHeaders, raw_body: bytes, webhook_id: str) -> None:
        if headers.auth_algo.upper() not in {"SHA256WITHRSA"}:
            raise WebhookVerificationError(f"Unsupported auth algorithm {headers.auth_algo!r}")
        crc = zlib.crc32(raw_body) & 0xFFFFFFFF
        message = f"{headers.transmission_id}|{headers.transmission_time}|{webhook_id}|{crc}"
        try:
            signature = base64.b64decode(headers.transmission_sig, validate=True)
        except ValueError as exc:
            raise WebhookVerificationError("Signature is not valid base64") from exc
        public_key = self._certificate(headers.cert_url).public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise WebhookVerificationError("Certificate key is not RSA")
        try:
            public_key.verify(signature, message.encode(), padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature as exc:
            raise WebhookVerificationError("Signature does not match") from exc


def parse_headers(get: Callable[[str], str | None]) -> WebhookHeaders:
    names = {
        "transmission_id": "paypal-transmission-id",
        "transmission_time": "paypal-transmission-time",
        "cert_url": "paypal-cert-url",
        "auth_algo": "paypal-auth-algo",
        "transmission_sig": "paypal-transmission-sig",
    }
    values = {k: get(h) for k, h in names.items()}
    missing = [names[k] for k, v in values.items() if not v]
    if missing:
        raise WebhookVerificationError(f"Missing headers: {', '.join(missing)}")
    return WebhookHeaders(**{k: str(v) for k, v in values.items()})


def classify_verification(
    verifier: SignatureVerifier,
    headers: WebhookHeaders,
    raw_body: bytes,
    configured_webhook_id: str | None,
    *,
    accept_simulator: bool,
) -> EventVerification:
    """Return VERIFIED for genuine app events, FIXTURE for simulator events (when allowed).

    Raises WebhookVerificationError when neither applies. Unverified events are rejected."""
    if configured_webhook_id:
        try:
            verifier.verify(headers, raw_body, configured_webhook_id)
            return EventVerification.VERIFIED
        except WebhookVerificationError:
            if not accept_simulator:
                raise
    if accept_simulator:
        verifier.verify(headers, raw_body, SIMULATOR_WEBHOOK_ID)
        return EventVerification.FIXTURE
    raise WebhookVerificationError("No webhook id configured")


def store_event(
    db: Session, raw_body: bytes, verification: EventVerification, transmission_id: str | None
) -> tuple[PaymentEvent, bool]:
    """Persist the event exactly once. Returns (event, created)."""
    try:
        payload = json.loads(raw_body)
    except ValueError as exc:
        raise WebhookVerificationError("Body is not JSON") from exc
    event_id = str(payload.get("id") or "")
    event_type = str(payload.get("event_type") or "")
    if not event_id or not event_type:
        raise WebhookVerificationError("Event id or type missing")

    existing = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == event_id))
    if existing is not None:
        existing.delivery_count += 1
        db.commit()
        return existing, False

    sha = hashlib.sha256(raw_body).hexdigest()
    raw = db.scalar(select(RawPayload).where(RawPayload.sha256 == sha))
    if raw is None:
        raw = RawPayload(sha256=sha, body=raw_body)
        db.add(raw)
        db.flush()
    resource = payload.get("resource") or {}
    event = PaymentEvent(
        provider_event_id=event_id,
        provider_event_type=event_type,
        resource_id=str(resource.get("id")) if resource.get("id") else None,
        payload_sha256=sha,
        payload_reference=raw.id,
        transmission_id=transmission_id,
        verification_status=verification,
        processing_status=EventProcessing.RECEIVED,
        data_origin=(
            DataOrigin.LIVE_SANDBOX
            if verification is EventVerification.VERIFIED
            else DataOrigin.SIMULATED
        ),
        occurred_at=_parse_time(payload.get("create_time")),
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        dup = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == event_id))
        assert dup is not None
        return dup, False
    return event, True


# Status precedence prevents late/out-of-order events from regressing state.
_RANK = {
    TransactionStatus.ORDER_CREATED: 0,
    TransactionStatus.CAPTURE_PENDING: 1,
    TransactionStatus.CAPTURE_FAILED: 1,
    TransactionStatus.CAPTURE_DECLINED: 2,
    TransactionStatus.CAPTURED: 2,
    TransactionStatus.PARTIALLY_REFUNDED: 3,
    TransactionStatus.REFUNDED: 4,
}

_CAPTURE_EVENTS = {
    "PAYMENT.CAPTURE.COMPLETED": TransactionStatus.CAPTURED,
    "PAYMENT.CAPTURE.PENDING": TransactionStatus.CAPTURE_PENDING,
    "PAYMENT.CAPTURE.DENIED": TransactionStatus.CAPTURE_DECLINED,
    "PAYMENT.CAPTURE.DECLINED": TransactionStatus.CAPTURE_DECLINED,
    "PAYMENT.CAPTURE.REFUNDED": TransactionStatus.REFUNDED,
    "PAYMENT.CAPTURE.REVERSED": TransactionStatus.REFUNDED,
}


def process_event(db: Session, event_id: Any) -> PaymentEvent:
    event = db.scalar(select(PaymentEvent).where(PaymentEvent.id == event_id).with_for_update())
    if event is None:
        raise LookupError("event not found")
    if event.processing_status in (EventProcessing.PROCESSED, EventProcessing.IGNORED):
        db.rollback()
        return event
    event.attempts += 1
    try:
        raw = db.get(RawPayload, event.payload_reference)
        assert raw is not None
        payload = json.loads(raw.body)
        outcome = _apply(db, event, payload)
        event.processing_status = outcome
        event.processed_at = datetime.now(UTC)
        if outcome is EventProcessing.PROCESSED:
            event.error_reason = None
    except Exception as exc:
        db.rollback()
        event = db.scalar(select(PaymentEvent).where(PaymentEvent.id == event_id))
        assert event is not None
        event.attempts += 1
        event.processing_status = EventProcessing.FAILED
        event.error_reason = f"{type(exc).__name__}: {exc}"[:500]
        log.exception(
            "webhook processing failed", extra={"data": {"event": event.provider_event_id}}
        )
    db.commit()
    return event


def _apply(db: Session, event: PaymentEvent, payload: dict[str, Any]) -> EventProcessing:
    resource = payload.get("resource") or {}
    etype = event.provider_event_type
    target = _CAPTURE_EVENTS.get(etype)

    order_id: str | None = None
    capture_id: str | None = None
    if etype.startswith("PAYMENT.CAPTURE."):
        related = ((resource.get("supplementary_data") or {}).get("related_ids")) or {}
        order_id = related.get("order_id")
        capture_id = resource.get("id")
        if etype in ("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED"):
            # The resource is the refund; the capture is linked via the "up" link.
            capture_id = _capture_from_links(resource) or capture_id
    elif etype.startswith("CHECKOUT.ORDER."):
        order_id = resource.get("id")

    clauses = []
    if capture_id:
        clauses.append(Transaction.paypal_capture_id == capture_id)
    if order_id:
        clauses.append(Transaction.paypal_order_id == order_id)
    txn = (
        db.scalar(select(Transaction).where(or_(*clauses)).with_for_update(of=Transaction))
        if clauses
        else None
    )
    if txn is None:
        event.error_reason = "No matching SENTINEL transaction for this event"
        return EventProcessing.IGNORED

    event.transaction_id = txn.id
    event.merchant_id = txn.merchant_id
    if (
        event.data_origin is not DataOrigin.LIVE_SANDBOX
        or txn.data_origin is not DataOrigin.LIVE_SANDBOX
    ):
        # Simulator events are recorded and linked but never mutate real sandbox records.
        event.error_reason = "Simulated event linked for reference; transaction not modified"
        return EventProcessing.IGNORED

    if target is not None:
        if (
            capture_id
            and not txn.paypal_capture_id
            and etype in ("PAYMENT.CAPTURE.COMPLETED", "PAYMENT.CAPTURE.PENDING")
        ):
            txn.paypal_capture_id = capture_id
        if target is TransactionStatus.REFUNDED and etype == "PAYMENT.CAPTURE.REFUNDED":
            target = _refund_status(resource, txn)
        if target in (TransactionStatus.REFUNDED, TransactionStatus.PARTIALLY_REFUNDED):
            # First refund time feeds the payer's prior-refund risk feature.
            txn.refunded_at = txn.refunded_at or event.occurred_at or datetime.now(UTC)
        if _RANK[target] >= _RANK[txn.status] and txn.status is not target:
            previous = txn.status
            txn.status = target
            audit.record(
                db,
                action="paypal.webhook.status_applied",
                entity_type="transaction",
                entity_id=txn.id,
                merchant_id=txn.merchant_id,
                actor_id=None,
                actor_type="PAYPAL_WEBHOOK",
                metadata={
                    "event": event.provider_event_id,
                    "from": previous.value,
                    "to": target.value,
                },
            )
    return EventProcessing.PROCESSED


def _refund_status(resource: dict[str, Any], txn: Transaction) -> TransactionStatus:
    breakdown = resource.get("seller_payable_breakdown") or {}
    total = breakdown.get("total_refunded_amount")
    if total:
        refunded = Money.from_paypal(str(total["value"]), str(total["currency_code"]))
        if refunded.currency == txn.currency and refunded.amount_minor < txn.amount_minor:
            return TransactionStatus.PARTIALLY_REFUNDED
    return TransactionStatus.REFUNDED


def _capture_from_links(resource: dict[str, Any]) -> str | None:
    for link in resource.get("links") or []:
        if link.get("rel") == "up":
            href = str(link.get("href", ""))
            if "/captures/" in href:
                return href.rstrip("/").rsplit("/", 1)[-1]
    return None


def pending_event_ids(db: Session, limit: int = 50) -> list[Any]:
    rows = db.scalars(
        select(PaymentEvent.id)
        .where(
            PaymentEvent.processing_status.in_([EventProcessing.RECEIVED, EventProcessing.FAILED]),
            PaymentEvent.attempts < MAX_PROCESSING_ATTEMPTS,
        )
        .order_by(PaymentEvent.received_at)
        .limit(limit)
    )
    return list(rows)


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
