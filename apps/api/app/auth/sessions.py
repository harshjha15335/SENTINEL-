import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSession

SESSION_COOKIE = "sentinel_session"
CSRF_COOKIE = "sentinel_csrf"
CSRF_HEADER = "x-csrf-token"


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class IssuedSession:
    session_token: str
    csrf_token: str
    expires_at: datetime


def issue_session(db: Session, user: User, ttl_minutes: int) -> IssuedSession:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    db.add(
        UserSession(
            user_id=user.id,
            token_digest=digest(token),
            csrf_digest=digest(csrf),
            expires_at=expires,
        )
    )
    return IssuedSession(token, csrf, expires)


def find_active_session(db: Session, token: str) -> UserSession | None:
    row = db.scalar(select(UserSession).where(UserSession.token_digest == digest(token)))
    if row is None or row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        return None
    return row


def revoke(db: Session, row: UserSession) -> None:
    row.revoked_at = datetime.now(UTC)
