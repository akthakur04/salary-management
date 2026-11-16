"""Password checks and signed session tokens for the single HR login.

The session is a short-lived JWT (HS256) in an HttpOnly cookie, so page scripts
can't read it. FastAPI checks it on every protected route.
"""

import hmac
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.errors import UnauthenticatedError

SESSION_COOKIE = "session"
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def normalise_email(email: str) -> str:
    return email.strip().lower()


def credentials_match(email: str, password: str, expected_email: str, password_hash: str) -> bool:
    """Compare in constant time, and always run bcrypt, so a wrong email takes as long."""
    email_matches = hmac.compare_digest(
        normalise_email(email).encode(), normalise_email(expected_email).encode()
    )
    password_matches = bcrypt.checkpw(password.encode(), password_hash.encode())
    return email_matches and password_matches


def create_session_token(
    email: str, secret: str, lifetime: timedelta, issued_at: datetime | None = None
) -> str:
    issued = issued_at or datetime.now(UTC)
    claims = {"sub": email, "iat": issued, "exp": issued + lifetime}
    return jwt.encode(claims, secret, algorithm=_ALGORITHM)


def read_session_token(token: str, secret: str) -> str:
    """The signed-in email. A missing, expired, forged or tampered token is unauthenticated."""
    try:
        claims = jwt.decode(
            token, secret, algorithms=[_ALGORITHM], options={"require": ["sub", "exp"]}
        )
    except jwt.InvalidTokenError as error:
        raise UnauthenticatedError("Your session has ended. Sign in again.") from error
    return str(claims["sub"])
