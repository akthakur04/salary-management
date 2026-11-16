"""Fixed reference FX rates, used to compare pay across countries in USD.

USD figures are always computed at read time against the active rate set, never
stored, so a rate update applies everywhere at once. A missing rate is an error,
never a silent zero.
"""

from collections.abc import Iterable, Mapping
from decimal import Decimal
from types import MappingProxyType

from app.domain.errors import InvalidFxRateError, MissingFxRateError
from app.domain.money import Money

USD = "USD"


class FxRates:
    def __init__(self, usd_per_unit: Mapping[str, Decimal]) -> None:
        invalid = sorted(currency for currency, rate in usd_per_unit.items() if rate <= 0)
        if invalid:
            raise InvalidFxRateError("FX rates must be greater than zero.", currencies=invalid)
        self._usd_per_unit = MappingProxyType({USD: Decimal(1), **usd_per_unit})

    def to_usd(self, money: Money) -> Money:
        rate = self._usd_per_unit.get(money.currency)
        if rate is None:
            raise MissingFxRateError(
                f"There's no reference FX rate for {money.currency}.", currency=money.currency
            )
        return Money(money.times(rate).amount_minor, USD)

    def ensure_covers(self, currencies: Iterable[str]) -> None:
        """Fail at configuration time if any currency in use has no rate."""
        missing = sorted(set(currencies) - self._usd_per_unit.keys())
        if missing:
            raise MissingFxRateError(
                "The active FX rate set is missing currencies that are in use.",
                currencies=missing,
            )
