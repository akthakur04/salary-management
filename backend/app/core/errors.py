"""Application errors. Raise these from services; the API layer turns them into responses."""

from typing import Any, ClassVar


class AppError(Exception):
    """Base for every error the API reports deliberately.

    Subclasses set the HTTP status and a default code. A raise site may pass a
    more specific code (e.g. `OVERLAPPING_VERSION`) for clients to act on.
    """

    status_code: ClassVar[int] = 400
    default_code: ClassVar[str] = "BAD_REQUEST"

    def __init__(
        self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    default_code = "NOT_FOUND"
