"""Authentication and authorization dependencies. Roles are enforced here, server-side."""

import hmac
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.sessions import CSRF_HEADER, SESSION_COOKIE, digest, find_active_session
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.db.session import get_db
from app.models import User, UserSession
from app.models.enums import Role

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class Principal:
    user: User
    session: UserSession

    @property
    def merchant_id(self) -> uuid.UUID:
        return self.user.merchant_id

    @property
    def role(self) -> Role:
        return self.user.role


def current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthenticationError("Sign in required")
    row = find_active_session(db, token)
    if row is None:
        raise AuthenticationError("Session expired or invalid")
    if request.method not in _SAFE_METHODS:
        supplied = request.headers.get(CSRF_HEADER, "")
        if not supplied or not hmac.compare_digest(digest(supplied), row.csrf_digest):
            raise PermissionDeniedError("Missing or invalid CSRF token")
    return Principal(user=row.user, session=row)


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    allowed = set(roles)

    def _check(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in allowed:
            raise PermissionDeniedError(
                "Your role does not permit this action",
                details={"required": sorted(r.value for r in allowed)},
            )
        return principal

    return _check


any_member = require_roles(Role.ADMIN, Role.ANALYST, Role.VIEWER)
operator = require_roles(Role.ADMIN, Role.ANALYST)
admin_only = require_roles(Role.ADMIN)
