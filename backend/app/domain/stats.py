"""Aggregates for insights: pay summaries and band distribution.

Percentiles are computed here rather than in SQL, so results are identical on
SQLite and Postgres (SQLite has no percentile function). Inputs are minor units
in one currency, typically USD at reference rates.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.bands import BandPosition
from app.domain.money import round_half_even


@dataclass(frozen=True, slots=True)
class PaySummary:
    count: int
    minimum: int
    median: int
    mean: int
    maximum: int


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


def _median(sorted_values: list[int]) -> int:
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[middle]
    return round_half_even(Decimal(sorted_values[middle - 1] + sorted_values[middle]) / 2)
