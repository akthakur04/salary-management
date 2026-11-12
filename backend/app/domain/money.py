"""Money as whole minor units (cents, paise) plus an ISO 4217 currency code. Never a float.

Every supported currency (USD, GBP, EUR, INR, SGD, BRL, CAD, AUD) has two minor
digits, so minor units convert between currencies at the quoted rate directly.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Self

from app.domain.errors import CurrencyMismatchError, InvalidAmountError, InvalidCurrencyError

_ISO_4217 = re.compile(r"[A-Z]{3}")


def round_half_even(value: Decimal) -> int:
    """Round to a whole number of minor units; ties go to the even neighbour."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise InvalidAmountError(
                "Amounts are whole minor units (e.g. cents), never fractions.",
                amount=repr(self.amount_minor),
            )
        if not _ISO_4217.fullmatch(self.currency):
            raise InvalidCurrencyError(
                "Currency must be a three-letter ISO 4217 code, such as INR.",
                currency=self.currency,
            )

    @classmethod
    def zero(cls, currency: str) -> Self:
        return cls(0, currency)

    def is_positive(self) -> bool:
        return self.amount_minor > 0

    def times(self, factor: Decimal) -> "Money":
        return Money(round_half_even(self.amount_minor * factor), self.currency)

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount_minor < other.amount_minor

    def __le__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount_minor <= other.amount_minor

    def __gt__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount_minor > other.amount_minor

    def __ge__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        return self.amount_minor >= other.amount_minor

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                "Amounts in different currencies can't be combined or compared directly.",
                currencies=[self.currency, other.currency],
            )
