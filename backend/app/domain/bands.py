"""Pay bands and how an employee's base salary compares to theirs.

Comparison uses the full-time-equivalent base, so part-time pay is judged fairly.
Contractors are never banded. The comparison is computed at read time against the
current band, never stored, because bands are revised.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from app.domain.employment import EmploymentType, validate_fte
from app.domain.errors import CurrencyMismatchError, InvalidPayBandError
from app.domain.money import Money, round_half_even

_TWO_DECIMALS = Decimal("0.01")


class BandPosition(StrEnum):
    BELOW = "below"
    IN_BAND = "in_band"
    ABOVE = "above"
    NO_BAND = "no_band"


@dataclass(frozen=True, slots=True)
class PayBand:
    minimum: Money
    midpoint: Money
    maximum: Money

    def __post_init__(self) -> None:
        if not (self.minimum.currency == self.midpoint.currency == self.maximum.currency):
            raise CurrencyMismatchError(
                "A pay band's minimum, midpoint and maximum must share one currency.",
                currencies=[self.minimum.currency, self.midpoint.currency, self.maximum.currency],
            )
        if not (self.minimum.is_positive() and self.minimum <= self.midpoint <= self.maximum):
            raise InvalidPayBandError(
                "A pay band needs 0 < minimum ≤ midpoint ≤ maximum.",
                minimum_minor=self.minimum.amount_minor,
                midpoint_minor=self.midpoint.amount_minor,
                maximum_minor=self.maximum.amount_minor,
            )

    @property
    def currency(self) -> str:
        return self.minimum.currency


@dataclass(frozen=True, slots=True)
class BandComparison:
    position: BandPosition
    fte_equivalent_base: Money
    compa_ratio: Decimal | None
    gap_to_minimum: Money | None


def fte_equivalent(base_annual: Money, fte: Decimal) -> Money:
    return Money(round_half_even(base_annual.amount_minor / fte), base_annual.currency)


def compare_to_band(
    base_annual: Money,
    fte: Decimal,
    employment_type: EmploymentType,
    band: PayBand | None,
) -> BandComparison:
    validate_fte(employment_type, fte)
    equivalent = fte_equivalent(base_annual, fte)
    if band is None or employment_type is EmploymentType.CONTRACTOR:
        return BandComparison(BandPosition.NO_BAND, equivalent, None, None)
    if band.currency != equivalent.currency:
        raise CurrencyMismatchError(
            "Pay and pay band must be in the same currency to compare them.",
            currencies=[equivalent.currency, band.currency],
        )

    compa_ratio = (Decimal(equivalent.amount_minor) / band.midpoint.amount_minor).quantize(
        _TWO_DECIMALS, rounding=ROUND_HALF_EVEN
    )
    if equivalent < band.minimum:
        return BandComparison(
            BandPosition.BELOW, equivalent, compa_ratio, band.minimum - equivalent
        )
    position = BandPosition.ABOVE if equivalent > band.maximum else BandPosition.IN_BAND
    return BandComparison(position, equivalent, compa_ratio, None)
