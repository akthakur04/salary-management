"""Aggregates for insights: pay summaries and band distribution.

Percentiles are computed here rather than in SQL, so results are identical on
SQLite and Postgres (SQLite has no percentile function). Inputs are minor units
in one currency, typically USD at reference rates.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from app.domain.bands import BandPosition
from app.domain.money import round_half_even

_ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True, slots=True)
class PaySummary:
    count: int
    minimum: int
    median: int
    mean: int
    maximum: int


@dataclass(frozen=True, slots=True)
class PayBucket:
    """People paid at least `lower` and less than `upper` (minor units)."""

    lower: int
    upper: int
    count: int


@dataclass(frozen=True, slots=True)
class BandDistribution:
    below: int
    in_band: int
    above: int

    @property
    def banded(self) -> int:
        return self.below + self.in_band + self.above


def summarise_pay(amounts_minor: Iterable[int | None]) -> PaySummary | None:
    """Summarise pay, skipping people with no package (None) rather than counting them as zero."""
    values = sorted(amount for amount in amounts_minor if amount is not None)
    if not values:
        return None
    return PaySummary(
        count=len(values),
        minimum=values[0],
        median=_median(values),
        mean=round_half_even(Decimal(sum(values)) / len(values)),
        maximum=values[-1],
    )


def band_distribution(positions: Iterable[BandPosition]) -> BandDistribution:
    """Count people against their bands. Unbanded staff (contractors) are left out."""
    counted = list(positions)
    return BandDistribution(
        below=counted.count(BandPosition.BELOW),
        in_band=counted.count(BandPosition.IN_BAND),
        above=counted.count(BandPosition.ABOVE),
    )


def share_percent(part: int | Decimal, whole: int | Decimal) -> Decimal | None:
    """`part` as a percentage of `whole`, to one decimal place; None when `whole` is zero."""
    if whole == 0:
        return None
    return (Decimal(part) * 100 / Decimal(whole)).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_EVEN)


_NICE_STEPS = (1, 2, Decimal("2.5"), 5, 10)


def pay_histogram(
    amounts_minor: Iterable[int | None], target_buckets: int = 12
) -> tuple[PayBucket, ...]:
    """Group pay into equal brackets with round widths (1, 2, 2.5 or 5 x a power of ten).

    People without a package (None) are left out. The highest amount always
    falls inside the last bracket.
    """
    values = sorted(amount for amount in amounts_minor if amount is not None)
    if not values:
        return ()
    low, high = values[0], values[-1]
    if low == high:
        return (PayBucket(low, low + 1, len(values)),)

    width = _nice_width(Decimal(high - low) / target_buckets)
    start = (low // width) * width
    counts = [0] * ((high - start) // width + 1)
    for value in values:
        counts[(value - start) // width] += 1
    return tuple(
        PayBucket(start + index * width, start + (index + 1) * width, count)
        for index, count in enumerate(counts)
    )


def _nice_width(raw: Decimal) -> int:
    magnitude = Decimal(10) ** (len(str(int(raw))) - 1) if raw >= 1 else Decimal(1)
    return int(next(step * magnitude for step in _NICE_STEPS if step * magnitude >= raw))


def _median(sorted_values: list[int]) -> int:
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return round_half_even(Decimal(sorted_values[middle - 1] + sorted_values[middle]) / 2)
