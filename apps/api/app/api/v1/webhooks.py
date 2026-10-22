import hashlib
import hmac
import json
from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, get_sessionmaker
from app.models.enums import EventVerification
from app.services.webhooks import (
    SignatureVerifier,
    WebhookVerificationError,
    WebhookVerificationUnavailable,
    classify_verification,
    parse_headers,
    process_event,
    store_event,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
MAX_BODY_BYTES = 256 * 1024


@lru_cache
def get_verifier() -> SignatureVerifier:
    return SignatureVerifier()


def _process_in_background(event_id: object) -> None:
    with get_sessionmaker()() as db:
        process_event(db, event_id)


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    verifier: SignatureVerifier = Depends(get_verifier),
) -> JSONResponse:
    raw = await request.body()  # exact bytes: required for the CRC32 in the signed message
    if len(raw) > MAX_BODY_BYTES:
        return JSONResponse({"error": {"code": "payload_too_large"}}, 413)
    settings = get_settings()
    try:
        headers = parse_headers(request.headers.get)
        verification = classify_verification(
            verifier,
            headers,
            raw,
            settings.paypal_webhook_id,
            # Simulator events are only accepted outside production-like environments.
            accept_simulator=settings.environment != "production",
        )
        event, created = store_event(
            db,
            raw,
            verification,
            headers.transmission_id,
            {k: v for k, v in request.headers.items() if k.startswith("paypal-")},
        )
    except WebhookVerificationUnavailable:
        return JSONResponse({"error": {"code": "verification_unavailable"}}, 503)
    except WebhookVerificationError as exc:
        return JSONResponse(
            {"error": {"code": "webhook_rejected", "message": str(exc)}}, status_code=400
        )
    # Event is committed before we acknowledge; processing happens after the response and
    # is re-driven by the worker if it fails.
    if created:
        background.add_task(_process_in_background, event.id)
    return _receipt(event, created)


def _receipt(event: object, created: bool) -> JSONResponse:
    from app.models import PaymentEvent

    assert isinstance(event, PaymentEvent)
    return JSONResponse(
        {
            "received": True,
            "duplicate": not created,
            "durable": True,
            "event_id": event.provider_event_id,
            "payload_sha256": event.payload_sha256,
            "verification_status": event.verification_status.value,
            "data_origin": event.data_origin.value,
        }
    )


@router.post("/fixtures/paypal", include_in_schema=False)
async def fixture_webhook(
    request: Request, background: BackgroundTasks, db: Session = Depends(get_db)
) -> JSONResponse:
    settings = get_settings()
    if (
        not settings.allow_webhook_fixtures
        or settings.environment == "production"
        or not settings.webhook_fixture_key
    ):
        return JSONResponse({"error": "not_found"}, 404)
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        return JSONResponse({"error": "payload_too_large"}, 413)
    expected = hmac.new(
        settings.webhook_fixture_key.get_secret_value().encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("x-sentinel-fixture-signature", "")):
        return JSONResponse({"error": "invalid_fixture_signature"}, 403)
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not str(payload.get("id", "")).startswith("FIXTURE-"):
            return JSONResponse({"error": "fixture_prefix_required"}, 400)
        event, created = store_event(
            db,
            raw,
            EventVerification.FIXTURE,
            "LOCAL_FIXTURE",
            {k: v for k, v in request.headers.items() if k.startswith("paypal-")},
        )
    except (ValueError, WebhookVerificationError):
        return JSONResponse({"error": "invalid_fixture"}, 400)
    if created:
        background.add_task(_process_in_background, event.id)
    return _receipt(event, created)
