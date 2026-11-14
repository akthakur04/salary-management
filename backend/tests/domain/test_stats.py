from app.domain.bands import BandPosition
from app.domain.stats import BandDistribution, PaySummary, band_distribution, summarise_pay


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
