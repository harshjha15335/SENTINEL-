from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member, current_principal
from app.auth.passwords import verify_password
from app.auth.rate_limit import SlidingWindowLimiter
from app.auth.sessions import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    find_active_session,
    issue_session,
    revoke,
)
from app.core.config import get_settings
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
)
from app.db.session import get_db
from app.models import User
from app.schemas.api import LoginRequest, MeOut, SessionOut
from app.services import audit
from app.services.demo.public_access import demo_viewer

router = APIRouter(tags=["auth"])
_settings = get_settings()
_limiter = SlidingWindowLimiter(
    _settings.login_rate_limit_attempts, _settings.login_rate_limit_window_seconds
)
_demo_limiter = SlidingWindowLimiter(8, 300)


@router.post("/auth/login", response_model=SessionOut)
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> SessionOut:
    settings = get_settings()
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{body.email.lower()}"
    if not _limiter.hit(key):
        raise RateLimitedError("Too many sign-in attempts. Try again later.")

    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        audit.record(
            db,
            action="auth.login_failed",
            entity_type="user",
            entity_id=None,
            merchant_id=user.merchant_id if user else None,
            actor_id=None,
            actor_type="ANONYMOUS",
            metadata={"email_domain": body.email.split("@")[-1]},
        )
        db.commit()
        raise AuthenticationError("Email or password is incorrect")

    _limiter.reset(key)
    issued = issue_session(db, user, settings.session_ttl_minutes)
    user.last_login_at = datetime.now(UTC)
    audit.record(
        db,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        merchant_id=user.merchant_id,
        actor_id=user.id,
    )
    db.commit()
    max_age = settings.session_ttl_minutes * 60
    response.set_cookie(
        SESSION_COOKIE,
        issued.session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    # Readable by the SPA so it can echo it in X-CSRF-Token (double-submit, server-checked).
    response.set_cookie(
        CSRF_COOKIE,
        issued.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    return SessionOut(
        user=MeOut.model_validate(user), csrf_token=issued.csrf_token, expires_at=issued.expires_at
    )


# UI-only guest entry; the external merchant API contract remains unchanged.
@router.post("/auth/demo", response_model=SessionOut, include_in_schema=False)
def enter_read_only_demo(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> SessionOut:
    """Public, rate-limited entry into the verified SYNTHETIC_DEMO viewer only."""
    settings = get_settings()
    if not settings.public_demo_login_enabled:
        raise NotFoundError("Read-only judge preview is unavailable")
    # Cross-site forms and CSRF must not silently replace a visitor's session.
    if request.headers.get("origin") != "https://sentinel-v2-staging.onrender.com":
        raise PermissionDeniedError("Use the SENTINEL website to open the demo")
    if request.headers.get("sec-fetch-site", "same-origin") != "same-origin":
        raise PermissionDeniedError("Cross-origin demo access is unavailable")
    existing = request.cookies.get(SESSION_COOKIE)
    if existing and find_active_session(db, existing) is not None:
        raise ConflictError("Sign out before switching to the read-only demo")
    client = request.client.host if request.client else "unknown"
    if not _demo_limiter.hit(client):
        raise RateLimitedError("Too many demo sessions from this connection")
    user = demo_viewer(db)
    if user is None:
        raise NotFoundError("Read-only judge scenario has not been prepared")
    ttl = min(settings.session_ttl_minutes, 45)
    issued = issue_session(db, user, ttl)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        SESSION_COOKIE,
        issued.session_token,
        max_age=ttl * 60,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        issued.csrf_token,
        max_age=ttl * 60,
        httponly=False,
        secure=True,
        samesite="strict",
        path="/",
    )
    return SessionOut(
        user=MeOut.model_validate(user),
        csrf_token=issued.csrf_token,
        expires_at=issued.expires_at,
    )


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    principal: Principal = Depends(current_principal),
    db: Session = Depends(get_db),
) -> Response:
    session = db.merge(principal.session)
    revoke(db, session)
    audit.record(
        db,
        action="auth.logout",
        entity_type="user",
        entity_id=principal.user.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
    )
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(any_member)) -> MeOut:
    return MeOut.model_validate(principal.user)
