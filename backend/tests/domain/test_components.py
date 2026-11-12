from datetime import date
from decimal import Decimal

import pytest

from app.domain.components import Component, ComponentBasis, ComponentType, Frequency
from app.domain.errors import (
    InvalidAmountError,
    InvalidComponentError,
    InvalidPercentageError,
    MissingPayoutDateError,
)
from app.domain.money import Money

BASE = Money(2_400_000_00, "INR")


def test_monthly_allowance_is_annualised_by_twelve() -> None:
    housing = Component.allowance("Housing allowance", Money(30_000_00, "INR"), Frequency.MONTHLY)

    assert housing.annual_value(BASE) == Decimal(360_000_00)


def test_annual_allowance_counts_once() -> None:
    relocation = Component.allowance("Transport", Money(50_000_00, "INR"), Frequency.ANNUAL)

    assert relocation.annual_value(BASE) == Decimal(50_000_00)


def test_percentage_bonus_is_a_share_of_base() -> None:
    bonus = Component.bonus_percent(Decimal("10"))

    assert bonus.annual_value(BASE) == Decimal(240_000_00)


def test_fixed_bonus_does_not_depend_on_base() -> None:
    bonus = Component.bonus_fixed(Money(1_00_000_00, "INR"))

    assert bonus.annual_value(BASE) == Decimal(1_00_000_00)


def test_one_time_payment_adds_nothing_to_recurring_pay() -> None:
    sign_on = Component.one_time("Sign-on bonus", Money(150_000_00, "INR"), date(2022, 3, 14))

    assert sign_on.annual_value(BASE) == Decimal(0)


def test_bonus_and_commission_are_variable_pay() -> None:
    assert Component.bonus_percent(Decimal("15")).is_variable
    assert Component.commission_percent(Decimal("50")).is_variable
    assert not Component.allowance("Meal", Money(2_200_00, "INR"), Frequency.MONTHLY).is_variable


@pytest.mark.parametrize("amount_minor", [0, -1])
def test_zero_or_negative_component_amount_is_rejected(amount_minor: int) -> None:
    with pytest.raises(InvalidAmountError):
        Component.allowance("Housing", Money(amount_minor, "INR"), Frequency.MONTHLY)


@pytest.mark.parametrize("percent", ["-1", "0", "100.01", "150"])
def test_bonus_percentage_outside_0_to_100_is_rejected(percent: str) -> None:
    with pytest.raises(InvalidPercentageError):
        Component.bonus_percent(Decimal(percent))


def test_commission_percentage_outside_0_to_100_is_rejected() -> None:
    with pytest.raises(InvalidPercentageError):
        Component.commission_percent(Decimal("120"))


def test_bonus_of_exactly_100_percent_is_allowed() -> None:
    assert Component.bonus_percent(Decimal("100")).annual_value(BASE) == Decimal(BASE.amount_minor)


def test_one_time_payment_without_payout_date_is_rejected() -> None:
    with pytest.raises(MissingPayoutDateError):
        Component(
            type=ComponentType.ONE_TIME,
            basis=ComponentBasis.FIXED_AMOUNT,
            frequency=Frequency.ONCE,
            label="Retention bonus",
            amount=Money(50_000_00, "INR"),
        )


def test_recurring_component_with_a_payout_date_is_rejected() -> None:
    with pytest.raises(InvalidComponentError):
        Component(
            type=ComponentType.ALLOWANCE,
            basis=ComponentBasis.FIXED_AMOUNT,
            frequency=Frequency.MONTHLY,
            label="Housing",
            amount=Money(30_000_00, "INR"),
            payout_date=date(2026, 1, 1),
        )


def test_allowance_cannot_be_a_percentage_of_base() -> None:
    with pytest.raises(InvalidComponentError):
        Component(
            type=ComponentType.ALLOWANCE,
            basis=ComponentBasis.PERCENT_OF_BASE,
            frequency=Frequency.ANNUAL,
            label="Housing",
            percent=Decimal("10"),
        )


@pytest.mark.parametrize(
    ("component_type", "frequency"),
    [
        (ComponentType.BONUS, Frequency.MONTHLY),
        (ComponentType.COMMISSION, Frequency.ONCE),
        (ComponentType.ALLOWANCE, Frequency.ONCE),
        (ComponentType.ONE_TIME, Frequency.ANNUAL),
    ],
)
def test_component_with_a_frequency_its_type_does_not_allow_is_rejected(
    component_type: ComponentType, frequency: Frequency
) -> None:
    with pytest.raises(InvalidComponentError):
        Component(
            type=component_type,
            basis=ComponentBasis.FIXED_AMOUNT,
            frequency=frequency,
            label="Pay",
            amount=Money(1_000_00, "INR"),
            payout_date=date(2026, 1, 1) if frequency is Frequency.ONCE else None,
        )


def test_fixed_amount_component_needs_an_amount_and_no_percentage() -> None:
    with pytest.raises(InvalidComponentError):
        Component(
            type=ComponentType.BONUS,
            basis=ComponentBasis.FIXED_AMOUNT,
            frequency=Frequency.ANNUAL,
            label="Annual bonus",
            percent=Decimal("10"),
        )


def test_percentage_component_needs_a_percentage_and_no_amount() -> None:
    with pytest.raises(InvalidComponentError):
        Component(
            type=ComponentType.BONUS,
            basis=ComponentBasis.PERCENT_OF_BASE,
            frequency=Frequency.ANNUAL,
            label="Annual bonus",
            amount=Money(1_000_00, "INR"),
        )
