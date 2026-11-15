from decimal import Decimal

from app.domain.bands import BandPosition
from app.domain.stats import (
    BandDistribution,
    PayBucket,
    PaySummary,
    band_distribution,
    pay_histogram,
    share_percent,
    summarise_pay,
)


def test_pay_summary_reports_count_min_median_mean_and_max() -> None:
    summary = summarise_pay([300, 100, 200])

    assert summary == PaySummary(count=3, minimum=100, median=200, mean=200, maximum=300)


def test_employee_without_a_package_is_excluded_from_averages_not_counted_as_zero() -> None:
    summary = summarise_pay([100, 300, None])

    assert summary is not None
    assert summary.count == 2
    assert summary.mean == 200
    assert summary.minimum == 100


def test_median_of_an_even_count_is_the_middle_pair_averaged_half_to_even() -> None:
    lower_tie = summarise_pay([1, 2, 3, 4])
    upper_tie = summarise_pay([1, 2, 5, 6])

    assert lower_tie is not None
    assert upper_tie is not None
    assert lower_tie.median == 2
    assert upper_tie.median == 4


def test_mean_is_rounded_half_to_even() -> None:
    summary = summarise_pay([1, 2])

    assert summary is not None
    assert summary.mean == 2


def test_summary_of_nobody_is_none() -> None:
    assert summarise_pay([]) is None
    assert summarise_pay([None]) is None


def test_contractors_are_excluded_from_band_distribution() -> None:
    positions = [
        BandPosition.BELOW,
        BandPosition.IN_BAND,
        BandPosition.IN_BAND,
        BandPosition.ABOVE,
        BandPosition.NO_BAND,
    ]

    distribution = band_distribution(positions)

    assert distribution == BandDistribution(below=1, in_band=2, above=1)
    assert distribution.banded == 4


def test_share_is_a_percentage_to_one_decimal_rounded_half_to_even() -> None:
    assert share_percent(2, 3) == Decimal("66.7")
    assert share_percent(Decimal("0.25"), Decimal("1000")) == Decimal("0.0")
    assert share_percent(Decimal("0.75"), Decimal("1000")) == Decimal("0.1")


def test_share_of_nothing_is_none() -> None:
    assert share_percent(0, 0) is None


def test_pay_histogram_uses_round_bucket_widths() -> None:
    buckets = pay_histogram([12_000_00, 48_000_00, 95_000_00], target_buckets=10)

    assert {bucket.upper - bucket.lower for bucket in buckets} == {10_000_00}
    assert (buckets[0].lower, buckets[-1].upper) == (10_000_00, 100_000_00)
    assert [bucket.count for bucket in buckets] == [1, 0, 0, 1, 0, 0, 0, 0, 1]


def test_pay_histogram_puts_the_highest_amount_in_the_last_bucket() -> None:
    buckets = pay_histogram([0, 100, 200], target_buckets=2)

    assert [(b.lower, b.upper, b.count) for b in buckets] == [
        (0, 100, 1),
        (100, 200, 1),
        (200, 300, 1),
    ]


def test_pay_histogram_skips_people_without_a_package() -> None:
    buckets = pay_histogram([50_000_00, None, 70_000_00], target_buckets=4)

    assert sum(bucket.count for bucket in buckets) == 2


def test_pay_histogram_of_one_amount_is_a_single_bucket() -> None:
    assert pay_histogram([42_000_00, 42_000_00]) == (PayBucket(42_000_00, 42_000_01, 2),)


def test_pay_histogram_of_nobody_is_empty() -> None:
    assert pay_histogram([]) == ()
    assert pay_histogram([None]) == ()
