from datetime import date, datetime, timedelta, timezone

from app.core.clock import Clock, FixedClock, SystemClock


def test_fixed_clock_always_returns_the_pinned_date() -> None:
    clock: Clock = FixedClock(date(2026, 11, 12))

    assert clock.today() == date(2026, 11, 12)
    assert clock.today() == date(2026, 11, 12)


def test_system_clock_reports_the_utc_date_not_the_local_one() -> None:
    late_evening_in_new_york = datetime(2026, 12, 31, 21, 0, tzinfo=timezone(timedelta(hours=-5)))
    clock: Clock = SystemClock(now=lambda: late_evening_in_new_york)

    assert clock.today() == date(2027, 1, 1)
