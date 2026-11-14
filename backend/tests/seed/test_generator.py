"""Invariants of the demo data generator, checked on a 2,000-employee sample."""

from collections import Counter
from decimal import Decimal

import pytest

from app.domain.bands import BandPosition, compare_to_band
from app.domain.employment import EmploymentStatus, EmploymentType, status_on
from app.domain.money import Money
from app.domain.role_defaults import RoleDefaultComponent, components_for_new_hire
from app.domain.versions import ChangeReason, current_version, ensure_valid_history, pending_changes
from app.seed.generator import SEED_TODAY, SeedData, SeedEmployee, generate
from app.seed.reference_data import COUNTRIES

CURRENCY = {country.code: country.currency for country in COUNTRIES}


@pytest.fixture(scope="module")
def sample() -> SeedData:
    return generate(employees=2_000)


def _share(count: int, total: int) -> float:
    return count / total


def _with_pay(sample: SeedData) -> list[SeedEmployee]:
    return [employee for employee in sample.employees if employee.versions]


def test_generator_is_deterministic() -> None:
    assert generate(employees=150) == generate(employees=150)
    assert generate(employees=150) != generate(employees=150, random_seed=7)


def test_generates_the_requested_number_of_employees_with_unique_codes_and_emails(
    sample: SeedData,
) -> None:
    codes = [employee.employee_code for employee in sample.employees]
    emails = [employee.email for employee in sample.employees]

    assert len(sample.employees) == 2_000
    assert len(set(codes)) == len(codes)
    assert len(set(emails)) == len(emails)


def test_job_architecture_has_eight_departments_and_125_roles_banded_in_every_country(
    sample: SeedData,
) -> None:
    assert len(sample.departments) == 8
    assert len(sample.roles) == 125
    assert len({(band.role_id, band.country_code) for band in sample.bands}) == 125 * 8


def test_every_history_is_valid_starts_with_a_hire_and_has_one_to_four_versions(
    sample: SeedData,
) -> None:
    for employee in _with_pay(sample):
        ensure_valid_history(employee.versions)
        assert employee.versions[0].reason is ChangeReason.HIRE
        assert employee.versions[0].effective_from == employee.hire_date
        assert 1 <= len(employee.versions) <= 4
        for version in employee.versions:
            assert version.package.currency == CURRENCY[version.country_code]


def test_employment_type_mix_matches_the_seed_shape(sample: SeedData) -> None:
    types = Counter(employee.employment_type for employee in sample.employees)
    total = len(sample.employees)

    assert _share(types[EmploymentType.FULL_TIME], total) == pytest.approx(0.85, abs=0.03)
    assert _share(types[EmploymentType.PART_TIME], total) == pytest.approx(0.08, abs=0.02)
    assert _share(types[EmploymentType.CONTRACTOR], total) == pytest.approx(0.07, abs=0.02)


def test_part_time_fte_is_between_zero_and_one(sample: SeedData) -> None:
    part_time = [e for e in sample.employees if e.employment_type is EmploymentType.PART_TIME]

    assert all(Decimal(0) < employee.fte < Decimal(1) for employee in part_time)


def test_about_five_percent_are_terminated_with_no_change_after_their_last_day(
    sample: SeedData,
) -> None:
    leavers = [
        employee
        for employee in sample.employees
        if status_on(employee.status, employee.termination_date, SEED_TODAY)
        is EmploymentStatus.TERMINATED
    ]

    assert _share(len(leavers), len(sample.employees)) == pytest.approx(0.05, abs=0.015)
    for employee in leavers:
        assert employee.termination_date is not None
        assert employee.hire_date <= employee.termination_date < SEED_TODAY
        assert pending_changes(employee.versions, employee.termination_date) == ()


def test_most_banded_employees_are_paid_within_their_band(sample: SeedData) -> None:
    bands = {(band.role_id, band.country_code): band.band for band in sample.bands}
    positions = []
    for employee in _with_pay(sample):
        version = current_version(employee.versions, SEED_TODAY)
        if version is None or employee.employment_type is EmploymentType.CONTRACTOR:
            continue
        band = bands[(version.role_id, version.country_code)]
        comparison = compare_to_band(
            version.package.base_annual, employee.fte, employee.employment_type, band
        )
        positions.append(comparison.position)

    counts = Counter(positions)
    assert _share(counts[BandPosition.IN_BAND], len(positions)) == pytest.approx(0.85, abs=0.03)
    assert counts[BandPosition.BELOW] > 0
    assert counts[BandPosition.ABOVE] > 0


def test_about_twenty_percent_override_a_role_default(sample: SeedData) -> None:
    defaults: dict[int, list[RoleDefaultComponent]] = {role.id: [] for role in sample.roles}
    for role_id, default in sample.role_defaults:
        defaults[role_id].append(default)
    eligible = overridden = 0
    for employee in _with_pay(sample):
        if employee.employment_type is EmploymentType.CONTRACTOR:
            continue
        version = employee.versions[-1]
        variable = tuple(c for c in version.package.components if c.is_variable)
        eligible += 1
        overridden += variable != components_for_new_hire(defaults[version.role_id])

    assert _share(overridden, eligible) == pytest.approx(0.20, abs=0.04)


def test_some_employees_have_future_dated_changes(sample: SeedData) -> None:
    with_pending = [e for e in _with_pay(sample) if pending_changes(e.versions, SEED_TODAY)]

    assert _share(len(with_pending), len(sample.employees)) == pytest.approx(0.04, abs=0.02)


def test_a_few_employees_have_no_compensation_record(sample: SeedData) -> None:
    without_pay = [employee for employee in sample.employees if not employee.versions]

    assert 1 <= len(without_pay) <= 10


def test_contractors_have_no_variable_pay(sample: SeedData) -> None:
    for employee in _with_pay(sample):
        if employee.employment_type is EmploymentType.CONTRACTOR:
            assert all(not c.is_variable for c in employee.versions[-1].package.components)


def test_ravi_kumar_matches_the_profile_design(sample: SeedData) -> None:
    (ravi,) = [e for e in sample.employees if e.employee_code == "EMP-04821"]
    version = current_version(ravi.versions, SEED_TODAY)

    assert ravi.name == "Ravi Kumar"
    assert [v.reason for v in ravi.versions] == [
        ChangeReason.HIRE,
        ChangeReason.MERIT,
        ChangeReason.PROMOTION,
        ChangeReason.MERIT,
    ]
    assert version is not None
    totals = version.totals
    assert totals.fixed_cash == Money(27_86_400_00, "INR")
    assert totals.total_target_compensation == Money(30_26_400_00, "INR")
    assert ravi.versions[0].package.one_time_total_for_year(2022) == Money(1_50_000_00, "INR")


def test_ravi_kumar_appears_exactly_once(sample: SeedData) -> None:
    assert [e.name for e in sample.employees].count("Ravi Kumar") == 1
