from datetime import date
from decimal import Decimal

import pytest

from app.domain.components import Component, Frequency
from app.domain.errors import CurrencyMismatchError, InvalidAmountError
from app.domain.money import Money
from app.domain.package import CompensationPackage


def inr(rupees: int) -> Money:
    return Money(rupees * 100, "INR")


def usd(dollars: int) -> Money:
    return Money(dollars * 100, "USD")


HOUSING = Component.allowance("Housing allowance", inr(30_000), Frequency.MONTHLY)
MEAL = Component.allowance("Meal allowance", inr(2_200), Frequency.MONTHLY)
SIGN_ON = Component.one_time("Sign-on bonus", inr(1_50_000), date(2022, 3, 14))


def ravis_package() -> CompensationPackage:
    """Ravi Kumar, Software Engineer L3, India, as shown on the profile design."""
    return CompensationPackage(
        base_annual=inr(24_00_000),
        components=(HOUSING, MEAL, Component.bonus_percent(Decimal("10")), SIGN_ON),
    )


def test_totals_match_ravis_profile() -> None:
    totals = ravis_package().totals()

    assert totals.fixed_cash == inr(27_86_400)
    assert totals.target_variable == inr(2_40_000)
    assert totals.total_target_compensation == inr(30_26_400)


def test_two_employees_in_the_same_role_can_have_different_bases() -> None:
    lower = CompensationPackage(base_annual=inr(22_00_000))
    higher = CompensationPackage(base_annual=inr(26_00_000))

    assert lower.totals().fixed_cash != higher.totals().fixed_cash


def test_employee_without_a_bonus_has_zero_target_variable() -> None:
    with_bonus = CompensationPackage(inr(24_00_000), (Component.bonus_percent(Decimal("10")),))
    without_bonus = CompensationPackage(inr(24_00_000))

    assert with_bonus.totals().target_variable == inr(2_40_000)
    assert without_bonus.totals().target_variable == inr(0)


def test_package_without_variable_pay_has_total_equal_to_fixed_cash() -> None:
    package = CompensationPackage(inr(24_00_000), (HOUSING,))

    totals = package.totals()

    assert totals.total_target_compensation == totals.fixed_cash == inr(27_60_000)


def test_multiple_allowances_are_each_annualised_and_summed() -> None:
    transport = Component.allowance("Transport", inr(12_000), Frequency.ANNUAL)
    package = CompensationPackage(inr(24_00_000), (HOUSING, MEAL, transport))

    assert package.totals().fixed_cash == inr(24_00_000 + 3_60_000 + 26_400 + 12_000)


def test_fixed_and_percentage_bonuses_are_both_supported() -> None:
    fixed = CompensationPackage(usd(100_000), (Component.bonus_fixed(usd(12_000)),))
    percent = CompensationPackage(usd(100_000), (Component.bonus_percent(Decimal("12")),))

    assert fixed.totals().target_variable == percent.totals().target_variable == usd(12_000)


def test_percentage_bonus_recalculates_when_base_changes() -> None:
    package = CompensationPackage(
        usd(100_000),
        (Component.bonus_percent(Decimal("10")), Component.bonus_fixed(usd(5_000), "Spot")),
    )

    raised = package.with_base(usd(120_000))

    assert raised.totals().target_variable == usd(12_000 + 5_000)


def test_sales_commission_counts_as_target_variable() -> None:
    package = CompensationPackage(usd(60_000), (Component.commission_fixed(usd(40_000)),))

    totals = package.totals()

    assert totals.target_variable == usd(40_000)
    assert totals.total_target_compensation == usd(100_000)


def test_fixed_and_variable_mix_shows_commission_as_variable() -> None:
    package = CompensationPackage(usd(60_000), (Component.commission_fixed(usd(40_000)),))

    assert package.variable_share_percent() == Decimal("40.0")


def test_mix_matches_ravis_profile() -> None:
    assert ravis_package().variable_share_percent() == Decimal("7.9")


def test_one_time_payments_are_never_included_in_total_pay() -> None:
    with_sign_on = ravis_package()
    without_sign_on = CompensationPackage(
        inr(24_00_000), (HOUSING, MEAL, Component.bonus_percent(Decimal("10")))
    )

    assert with_sign_on.totals() == without_sign_on.totals()


def test_one_time_payments_are_reported_for_the_year_they_are_paid() -> None:
    package = ravis_package()

    assert package.one_time_total_for_year(2022) == inr(1_50_000)
    assert package.one_time_total_for_year(2026) == inr(0)


def test_target_variable_is_rounded_once_after_summing_components() -> None:
    # 50% of 1.01 is 0.505 each. Rounding each first would give 0.50 + 0.50.
    package = CompensationPackage(
        Money(101, "USD"),
        (Component.bonus_percent(Decimal("50")), Component.commission_percent(Decimal("50"))),
    )

    assert package.totals().target_variable == Money(101, "USD")


@pytest.mark.parametrize("amount_minor", [0, -100])
def test_zero_or_negative_base_salary_is_rejected(amount_minor: int) -> None:
    with pytest.raises(InvalidAmountError):
        CompensationPackage(Money(amount_minor, "INR"))


def test_component_in_a_different_currency_from_base_is_rejected() -> None:
    with pytest.raises(CurrencyMismatchError):
        CompensationPackage(inr(24_00_000), (Component.bonus_fixed(usd(1_000)),))
