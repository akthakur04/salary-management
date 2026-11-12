from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import (
    CurrencyCountryMismatchError,
    InvalidChangeReasonError,
    InvalidEffectivePeriodError,
    OverlappingVersionError,
)
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.versions import (
    ChangeReason,
    CompensationChange,
    CompensationVersion,
    base_change_percent,
    changes_due_within,
    current_version,
    ensure_valid_history,
    pending_changes,
    plan_revision,
)

TODAY = date(2026, 11, 12)
SE_L3, SE_L4 = 103, 104


def inr_package(rupees: int) -> CompensationPackage:
    return CompensationPackage(Money(rupees * 100, "INR"))


def change(
    effective_from: date,
    rupees: int,
    reason: ChangeReason = ChangeReason.MERIT,
    role_id: int = SE_L3,
) -> CompensationChange:
    return CompensationChange(effective_from, reason, role_id, "IN", inr_package(rupees))


def history_of(*changes: CompensationChange) -> tuple[CompensationVersion, ...]:
    history: tuple[CompensationVersion, ...] = ()
    for next_change in changes:
        history = plan_revision(history, next_change, "INR").history_after(history)
    return history


HIRE = change(date(2024, 4, 1), 22_00_000, ChangeReason.HIRE)
MERIT = change(date(2025, 4, 1), 24_00_000)


def test_hire_opens_the_history_with_nothing_to_close() -> None:
    plan = plan_revision((), HIRE, "INR")

    assert plan.closed_previous is None
    assert plan.new_version.effective_from == date(2024, 4, 1)
    assert plan.new_version.effective_to is None


def test_revision_closes_the_previous_version_on_the_new_effective_date() -> None:
    history = history_of(HIRE)

    plan = plan_revision(history, MERIT, "INR")

    assert plan.closed_previous is not None
    assert plan.closed_previous.effective_to == date(2025, 4, 1)
    assert plan.new_version.effective_to is None


def test_new_version_stores_its_local_currency_totals() -> None:
    plan = plan_revision((), HIRE, "INR")

    assert plan.new_version.totals.total_target_compensation == Money(22_00_000_00, "INR")


def test_current_version_is_the_one_in_force_on_the_date() -> None:
    history = history_of(HIRE, MERIT)

    assert current_version(history, date(2025, 3, 31)) == history[0]
    assert current_version(history, date(2025, 4, 1)) == history[1]
    assert current_version(history, TODAY) == history[1]


def test_there_is_no_current_version_before_hire() -> None:
    assert current_version(history_of(HIRE), date(2024, 3, 31)) is None


def test_future_dated_raise_leaves_current_package_unchanged_until_its_date() -> None:
    history = history_of(HIRE, MERIT, change(date(2027, 1, 1), 26_88_000))

    in_force_today = current_version(history, TODAY)
    in_force_on_the_date = current_version(history, date(2027, 1, 1))

    assert in_force_today is not None
    assert in_force_on_the_date is not None
    assert in_force_today.package == inr_package(24_00_000)
    assert in_force_on_the_date.package == inr_package(26_88_000)


def test_future_dated_raise_is_listed_as_pending() -> None:
    history = history_of(HIRE, MERIT, change(date(2027, 1, 1), 26_88_000))

    (pending,) = pending_changes(history, TODAY)

    assert pending.effective_from == date(2027, 1, 1)


def test_only_changes_within_the_window_are_due_soon() -> None:
    soon = change(date(2026, 12, 20), 25_00_000)
    later = change(date(2027, 3, 1), 26_00_000)
    history = history_of(HIRE, MERIT, soon, later)

    due = changes_due_within(history, TODAY, days=60)

    assert [version.effective_from for version in due] == [date(2026, 12, 20)]


def test_backdated_correction_after_the_latest_version_is_allowed() -> None:
    history = history_of(HIRE, MERIT)
    correction = change(date(2025, 10, 1), 23_80_000, ChangeReason.CORRECTION)

    after = plan_revision(history, correction, "INR").history_after(history)

    assert len(after) == 3
    assert after[1].effective_to == date(2025, 10, 1)
    assert current_version(after, TODAY) == after[2]


def test_correction_on_the_latest_version_date_replaces_it_and_keeps_it_in_history() -> None:
    history = history_of(HIRE, MERIT)
    correction = change(date(2025, 4, 1), 23_90_000, ChangeReason.CORRECTION)

    after = plan_revision(history, correction, "INR").history_after(history)

    superseded, corrected = after[1], after[2]
    assert superseded.package == inr_package(24_00_000)
    assert superseded.effective_from == superseded.effective_to == date(2025, 4, 1)
    assert current_version(after, date(2025, 4, 1)) == corrected


def test_correction_dated_between_two_existing_versions_is_rejected() -> None:
    history = history_of(HIRE, MERIT)
    correction = change(date(2024, 10, 1), 22_50_000, ChangeReason.CORRECTION)

    with pytest.raises(OverlappingVersionError) as raised:
        plan_revision(history, correction, "INR")

    assert raised.value.details == {
        "effective_from": "2024-10-01",
        "latest_version_effective_from": "2025-04-01",
    }


def test_only_a_correction_can_replace_a_version_on_the_same_date() -> None:
    history = history_of(HIRE, MERIT)

    with pytest.raises(OverlappingVersionError):
        plan_revision(history, change(date(2025, 4, 1), 25_00_000), "INR")


def test_change_dated_before_a_pending_change_is_rejected() -> None:
    history = history_of(HIRE, MERIT, change(date(2027, 1, 1), 26_88_000))

    with pytest.raises(OverlappingVersionError):
        plan_revision(history, change(date(2026, 12, 1), 25_00_000), "INR")


def test_overlapping_effective_periods_are_rejected() -> None:
    first = CompensationVersion(
        date(2024, 1, 1), ChangeReason.HIRE, SE_L3, "IN", inr_package(1), date(2025, 1, 1)
    )
    overlapping = CompensationVersion(
        date(2024, 6, 1), ChangeReason.MERIT, SE_L3, "IN", inr_package(2)
    )

    with pytest.raises(OverlappingVersionError):
        ensure_valid_history((first, overlapping))


def test_history_with_two_open_versions_is_rejected() -> None:
    first = CompensationVersion(date(2024, 1, 1), ChangeReason.HIRE, SE_L3, "IN", inr_package(1))
    second = CompensationVersion(date(2025, 1, 1), ChangeReason.MERIT, SE_L3, "IN", inr_package(2))

    with pytest.raises(OverlappingVersionError):
        ensure_valid_history((first, second))


def test_history_whose_latest_version_is_closed_is_rejected() -> None:
    closed = CompensationVersion(
        date(2024, 1, 1), ChangeReason.HIRE, SE_L3, "IN", inr_package(1), date(2025, 1, 1)
    )

    with pytest.raises(InvalidEffectivePeriodError):
        ensure_valid_history((closed,))


def test_well_formed_history_is_accepted_in_any_order() -> None:
    history = history_of(HIRE, MERIT)

    ensure_valid_history(tuple(reversed(history)))


def test_version_cannot_end_before_it_starts() -> None:
    with pytest.raises(InvalidEffectivePeriodError):
        CompensationVersion(
            date(2025, 1, 1), ChangeReason.HIRE, SE_L3, "IN", inr_package(1), date(2024, 1, 1)
        )


def test_first_version_must_be_a_hire() -> None:
    with pytest.raises(InvalidChangeReasonError):
        plan_revision((), MERIT, "INR")


def test_hire_cannot_be_recorded_after_the_first_version() -> None:
    with pytest.raises(InvalidChangeReasonError):
        plan_revision(history_of(HIRE), change(date(2025, 1, 1), 1, ChangeReason.HIRE), "INR")


def test_promotion_moves_the_employee_to_the_new_role_from_its_effective_date() -> None:
    promotion = change(date(2027, 1, 1), 26_88_000, ChangeReason.PROMOTION, role_id=SE_L4)
    history = history_of(HIRE, MERIT, promotion)

    before, after = current_version(history, TODAY), current_version(history, date(2027, 1, 1))

    assert before is not None
    assert after is not None
    assert (before.role_id, after.role_id) == (SE_L3, SE_L4)


def test_transfer_starts_a_version_in_the_new_currency_and_keeps_old_figures() -> None:
    history = history_of(HIRE)
    transfer = CompensationChange(
        date(2025, 6, 1),
        ChangeReason.MARKET_ADJUSTMENT,
        SE_L3,
        "DE",
        CompensationPackage(Money(68_000_00, "EUR")),
    )

    after = plan_revision(history, transfer, "EUR").history_after(history)

    assert after[0].package == inr_package(22_00_000)
    assert (after[1].country_code, after[1].package.currency) == ("DE", "EUR")


def test_currency_that_does_not_match_the_country_is_rejected() -> None:
    euro_pay_in_india = CompensationChange(
        date(2024, 4, 1),
        ChangeReason.HIRE,
        SE_L3,
        "IN",
        CompensationPackage(Money(60_000_00, "EUR")),
    )

    with pytest.raises(CurrencyCountryMismatchError):
        plan_revision((), euro_pay_in_india, "INR")


def test_raise_percentage_is_calculated_in_local_currency() -> None:
    assert base_change_percent(inr_package(22_00_000), inr_package(24_00_000)) == Decimal("9.1")
    assert base_change_percent(inr_package(24_00_000), inr_package(23_71_200)) == Decimal("-1.2")


def test_raise_percentage_is_not_reported_across_a_currency_change() -> None:
    euro_package = CompensationPackage(Money(68_000_00, "EUR"))

    assert base_change_percent(inr_package(22_00_000), euro_package) is None
