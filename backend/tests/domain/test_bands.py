from decimal import Decimal

import pytest

from app.domain.bands import BandPosition, PayBand, compare_to_band
from app.domain.employment import EmploymentType
from app.domain.errors import CurrencyMismatchError, InvalidPayBandError
from app.domain.money import Money

FULL = Decimal("1")


def inr(rupees: int) -> Money:
    return Money(rupees * 100, "INR")


SE_L3_INDIA = PayBand(minimum=inr(22_00_000), midpoint=inr(27_00_000), maximum=inr(32_00_000))


def test_two_employees_in_the_same_role_each_get_their_own_compa_ratio() -> None:
    ravi = compare_to_band(inr(24_00_000), FULL, EmploymentType.FULL_TIME, SE_L3_INDIA)
    divya = compare_to_band(inr(27_60_000), FULL, EmploymentType.FULL_TIME, SE_L3_INDIA)

    assert ravi.compa_ratio == Decimal("0.89")
    assert divya.compa_ratio == Decimal("1.02")


@pytest.mark.parametrize(
    ("base", "position"),
    [
        (inr(21_10_000), BandPosition.BELOW),
        (inr(22_00_000), BandPosition.IN_BAND),
        (inr(27_00_000), BandPosition.IN_BAND),
        (inr(32_00_000), BandPosition.IN_BAND),
        (inr(32_00_001), BandPosition.ABOVE),
    ],
)
def test_band_position_is_inclusive_of_minimum_and_maximum(
    base: Money, position: BandPosition
) -> None:
    comparison = compare_to_band(base, FULL, EmploymentType.FULL_TIME, SE_L3_INDIA)

    assert comparison.position is position


def test_part_time_employee_is_compared_to_band_at_fte() -> None:
    band = PayBand(inr(7_00_000), inr(8_00_000), inr(9_00_000))

    comparison = compare_to_band(inr(4_00_000), Decimal("0.5"), EmploymentType.PART_TIME, band)

    assert comparison.fte_equivalent_base == inr(8_00_000)
    assert comparison.position is BandPosition.IN_BAND
    assert comparison.compa_ratio == Decimal("1.00")


def test_part_time_pay_that_looks_low_is_in_band_at_fte() -> None:
    band = PayBand(inr(14_00_000), inr(16_00_000), inr(18_00_000))

    comparison = compare_to_band(inr(9_60_000), Decimal("0.6"), EmploymentType.PART_TIME, band)

    assert comparison.position is BandPosition.IN_BAND


def test_contractor_has_no_band_and_no_compa_ratio() -> None:
    comparison = compare_to_band(inr(28_00_000), FULL, EmploymentType.CONTRACTOR, SE_L3_INDIA)

    assert comparison.position is BandPosition.NO_BAND
    assert comparison.compa_ratio is None


def test_employee_whose_role_has_no_band_in_their_country_shows_no_band() -> None:
    comparison = compare_to_band(inr(24_00_000), FULL, EmploymentType.FULL_TIME, None)

    assert comparison.position is BandPosition.NO_BAND
    assert comparison.compa_ratio is None


def test_gap_to_band_minimum_is_reported_for_below_band_pay() -> None:
    comparison = compare_to_band(inr(21_10_000), FULL, EmploymentType.FULL_TIME, SE_L3_INDIA)

    assert comparison.gap_to_minimum == inr(90_000)


def test_no_gap_is_reported_for_pay_in_band() -> None:
    comparison = compare_to_band(inr(24_00_000), FULL, EmploymentType.FULL_TIME, SE_L3_INDIA)

    assert comparison.gap_to_minimum is None


def test_band_in_a_different_currency_from_pay_is_rejected() -> None:
    usd_band = PayBand(Money(1, "USD"), Money(2, "USD"), Money(3, "USD"))

    with pytest.raises(CurrencyMismatchError):
        compare_to_band(inr(24_00_000), FULL, EmploymentType.FULL_TIME, usd_band)


@pytest.mark.parametrize(
    ("minimum", "midpoint", "maximum"),
    [
        (inr(30), inr(20), inr(40)),
        (inr(10), inr(50), inr(40)),
        (inr(0), inr(20), inr(40)),
    ],
)
def test_pay_band_requires_positive_minimum_midpoint_and_maximum_in_order(
    minimum: Money, midpoint: Money, maximum: Money
) -> None:
    with pytest.raises(InvalidPayBandError):
        PayBand(minimum, midpoint, maximum)


def test_pay_band_in_mixed_currencies_is_rejected() -> None:
    with pytest.raises(CurrencyMismatchError):
        PayBand(inr(10), Money(20, "USD"), inr(30))
