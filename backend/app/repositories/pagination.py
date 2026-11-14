"""Offset pagination. At 10k rows the offset cost is negligible and any column can be sorted."""

from dataclasses import dataclass

from app.core.errors import InvalidRequestError

MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    page: int
    page_size: int


def validate_page(page: int, page_size: int) -> None:
    if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise InvalidRequestError(
            f"Pages start at 1 and hold between 1 and {MAX_PAGE_SIZE} rows.",
            code="INVALID_PAGE",
            details={"page": page, "page_size": page_size},
        )
