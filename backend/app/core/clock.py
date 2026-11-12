"""Injectable source of "today".

What counts as an employee's current package depends on the date (future-dated
raises, E14), so services ask a `Clock` instead of calling `date.today()`.
Tests use `FixedClock` to pin the date.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    def today(self) -> date: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SystemClock:
    """The real date, always in UTC so results don't depend on the server's timezone."""

    def __init__(self, now: Callable[[], datetime] = _utc_now) -> None:
        self._now = now

    def today(self) -> date:
        return self._now().astimezone(UTC).date()


class FixedClock:
    def __init__(self, pinned: date) -> None:
        self._pinned = pinned

    def today(self) -> date:
        return self._pinned
