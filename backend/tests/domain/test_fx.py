from decimal import Decimal

import pytest

from app.domain.errors import InvalidFxRateError, MissingFxRateError
from app.domain.fx import FxRates
from app.domain.money import Money

RATES = FxRates({"USD": Decimal("1"), "INR": Decimal("0.012"), "EUR": Decimal("1.08")})


def test_local_amount_is_converted_to_usd_at_the_reference_rate() -> None:
    ravis_total_pay = Money(30_26_400_00, "INR")

    assert RATES.to_usd(ravis_total_pay) == Money(36_316_80, "USD")


def test_usd_amount_converts_to_itself() -> None:
    assert RATES.to_usd(Money(123_45, "USD")) == Money(123_45, "USD")


def test_usd_conversion_rounds_half_to_even() -> None:
    rates = FxRates({"EUR": Decimal("0.5")})

    assert rates.to_usd(Money(5, "EUR")) == Money(2, "USD")
    assert rates.to_usd(Money(7, "EUR")) == Money(4, "USD")


def test_missing_fx_rate_fails_loudly_instead_of_returning_zero() -> None:
    with pytest.raises(MissingFxRateError) as raised:
        RATES.to_usd(Money(1_000_00, "BRL"))

    assert raised.value.details == {"currency": "BRL"}


def test_rate_set_must_cover_every_currency_in_use() -> None:
    with pytest.raises(MissingFxRateError) as raised:
        RATES.ensure_covers({"INR", "EUR", "BRL", "SGD"})

    assert raised.value.details == {"currencies": ["BRL", "SGD"]}


def test_rate_set_covering_every_currency_is_accepted() -> None:
    RATES.ensure_covers({"INR", "EUR"})


@pytest.mark.parametrize("rate", ["0", "-1.2"])
def test_fx_rates_must_be_positive(rate: str) -> None:
    with pytest.raises(InvalidFxRateError):
        FxRates({"INR": Decimal(rate)})
