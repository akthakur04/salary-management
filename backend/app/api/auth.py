"""Sign in, sign out, and who is signed in. Only login is public."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_settings_from_app, require_session
from app.core.config import Settings
from app.core.errors import UnauthenticatedError
from app.core.security import (
    SESSION_COOKIE,
    create_session_token,
    credentials_match,
    normalise_email,
)
from app.schemas.auth import LoginRequest, SessionUser

public_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = "That email and password don't match. Check both and try again."


@public_router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> SessionUser:
    if not credentials_match(
        body.email,
        body.password,
        settings.hr_admin_email,
        settings.hr_admin_password_hash.get_secret_value(),
    ):
        raise UnauthenticatedError(_INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    email = normalise_email(settings.hr_admin_email)
    lifetime = timedelta(hours=settings.session_hours)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(email, settings.session_secret.get_secret_value(), lifetime),
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessionUser(email=email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response, settings: Annotated[Settings, Depends(get_settings_from_app)]
) -> None:
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/"
    )


@router.get("/me")
def me(email: Annotated[str, Depends(require_session)]) -> SessionUser:
    return SessionUser(email=email)
