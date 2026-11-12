from decimal import Decimal

import pytest

from app.domain.errors import CurrencyMismatchError, InvalidAmountError, InvalidCurrencyError
from app.domain.money import Money, round_half_even


def test_money_adds_amounts_in_the_same_currency() -> None:
    assert Money(150, "EUR") + Money(250, "EUR") == Money(400, "EUR")


def test_money_subtracts_amounts_in_the_same_currency() -> None:
    assert Money(400, "EUR") - Money(150, "EUR") == Money(250, "EUR")


def test_adding_different_currencies_is_rejected() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(100, "EUR") + Money(100, "USD")


def test_comparing_different_currencies_is_rejected() -> None:
    with pytest.raises(CurrencyMismatchError):
        _ = Money(100, "EUR") < Money(200, "USD")


def test_money_compares_amounts_in_the_same_currency() -> None:
    small, large = Money(100, "INR"), Money(200, "INR")

    assert small < large
    assert small <= small
    assert large > small
    assert large >= large


@pytest.mark.parametrize("amount", [1.5, Decimal("1.5"), True])
def test_money_rejects_amounts_that_are_not_whole_minor_units(amount: object) -> None:
    with pytest.raises(InvalidAmountError):
        Money(amount, "USD")  # type: ignore[arg-type]


@pytest.mark.parametrize("currency", ["usd", "US", "USDT", ""])
def test_money_rejects_currency_codes_that_are_not_iso_4217(currency: str) -> None:
    with pytest.raises(InvalidCurrencyError):
        Money(100, currency)


def test_zero_money_has_no_amount() -> None:
    assert Money.zero("SGD") == Money(0, "SGD")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("2.5"), 2),
        (Decimal("3.5"), 4),
        (Decimal("-2.5"), -2),
        (Decimal("2.51"), 3),
        (Decimal("2.49"), 2),
    ],
)
def test_rounding_is_half_to_even(value: Decimal, expected: int) -> None:
    assert round_half_even(value) == expected


def test_multiplying_money_rounds_half_to_even() -> None:
    assert Money(5, "USD").times(Decimal("0.5")) == Money(2, "USD")
    assert Money(7, "USD").times(Decimal("0.5")) == Money(4, "USD")


def test_money_is_positive_only_above_zero() -> None:
    assert Money(1, "BRL").is_positive()
    assert not Money(0, "BRL").is_positive()
    assert not Money(-1, "BRL").is_positive()
