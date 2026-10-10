from functools import lru_cache

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, get_sessionmaker
from app.services.webhooks import (
    SignatureVerifier,
    WebhookVerificationError,
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
        event, created = store_event(db, raw, verification, headers.transmission_id)
    except WebhookVerificationError as exc:
        return JSONResponse(
            {"error": {"code": "webhook_rejected", "message": str(exc)}}, status_code=400
        )
    # Event is committed before we acknowledge; processing happens after the response and
    # is re-driven by the worker if it fails.
    if created:
        background.add_task(_process_in_background, event.id)
    return JSONResponse({"received": True, "duplicate": not created})
