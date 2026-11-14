"""The employee directory: current package as of a date, joined to bands and FX at read time."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.errors import InvalidRequestError
from app.domain.bands import BandPosition
from app.domain.components import ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.money import Money
from app.domain.versions import ChangeReason
from app.models import Employee
from app.repositories.employees import EmployeeQuery, EmployeeSort
from app.services.compensation import CompensationService
from app.services.directory import DirectoryEntry, DirectoryService
from app.services.employees import EmployeeService
from app.services.inputs import ComponentInput, RevisionRequest
from tests.integration.factories import Reference, hire_request, lakh

HOUSING = ComponentInput(
    ComponentType.ALLOWANCE,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.MONTHLY,
    "Housing allowance",
    amount_minor=lakh(30_000),
)
BONUS_15 = ComponentInput(
    ComponentType.BONUS,
    ComponentBasis.PERCENT_OF_BASE,
    Frequency.ANNUAL,
    "Annual bonus",
    percent=Decimal("15"),
)


@pytest.fixture
def directory(session: Session, reference: Reference, clock: FixedClock) -> DirectoryService:
    """Ten people covering the cases the directory must handle."""
    hire = EmployeeService(session).hire
    revise = CompensationService(session).revise

    def person(code: str, name: str, **overrides: object) -> int:
        email = f"{name.split()[0].lower()}@acme.example"
        return hire(
            hire_request(reference, employee_code=code, name=name, email=email, **overrides)
        )

    ravi = person("EMP-04821", "Ravi Kumar", components=(HOUSING,))
    revise(ravi, RevisionRequest(date(2025, 4, 1), ChangeReason.MERIT, lakh(24_00_000)))
    revise(
        ravi,
        RevisionRequest(
            date(2027, 1, 1),
            ChangeReason.PROMOTION,
            lakh(26_88_000),
            role_id=reference.se_l4_id,
            components=(HOUSING, BONUS_15),
        ),
    )
    person("EMP-03345", "Neha Gupta", base_annual_minor=lakh(21_10_000))
    person(
        "EMP-07408", "Vikram Singh", role_id=reference.se_l4_id, base_annual_minor=lakh(39_80_000)
    )
    person(
        "EMP-08812",
        "Arjun Mehta",
        employment_type=EmploymentType.PART_TIME,
        fte=Decimal("0.6"),
        base_annual_minor=lakh(13_20_000),
    )
    person(
        "EMP-05567",
        "Rahul Das",
        employment_type=EmploymentType.CONTRACTOR,
        base_annual_minor=lakh(28_00_000),
        components=(),
    )
    person("EMP-05874", "Hannah Clarke", country_code="DE", base_annual_minor=75_000_00)
    person(
        "EMP-00918",
        "Marcus Johnson",
        country_code="US",
        role_id=reference.ae_l2_id,
        base_annual_minor=58_000_00,
    )
    leaver = person("EMP-00001", "Old Timer")
    EmployeeService(session).terminate(leaver, date(2026, 6, 30))
    person("EMP-09121", "Sneha Patil", hire_date=date(2027, 2, 1))
    session.add(
        Employee(
            employee_code="EMP-02904",
            name="Priya Nair",
            email="priya@acme.example",
            employment_type=EmploymentType.FULL_TIME,
            fte=Decimal("1"),
            status=EmploymentStatus.ACTIVE,
            hire_date=date(2020, 1, 6),
        )
    )
    session.commit()
    return DirectoryService(session, clock)


def _names(entries: tuple[DirectoryEntry, ...]) -> list[str]:
    return [entry.record.name for entry in entries]


def _find(directory: DirectoryService, name: str, as_of: date | None = None) -> DirectoryEntry:
    page = directory.list(EmployeeQuery(q=name), as_of=as_of)
    (entry,) = page.items
    return entry


def test_current_package_is_the_one_in_force_today(directory: DirectoryService) -> None:
    ravi = _find(directory, "Ravi")

    assert ravi.record.current is not None
    assert ravi.record.current.base_annual_minor == lakh(24_00_000)
    assert ravi.record.current.effective_from == date(2025, 4, 1)
    assert ravi.record.role_title == "Software Engineer"


def test_future_promotion_changes_role_and_band_only_from_its_date(
    directory: DirectoryService,
) -> None:
    before = _find(directory, "Ravi", as_of=date(2026, 12, 31))
    after = _find(directory, "Ravi", as_of=date(2027, 1, 1))

    assert (before.record.role_title, before.record.level) == ("Software Engineer", 3)
    assert (after.record.role_title, after.record.level) == ("Senior Software Engineer", 4)
    assert before.band is not None
    assert after.band is not None
    assert before.band.position is BandPosition.IN_BAND
    assert after.band.position is BandPosition.BELOW


def test_band_comparison_uses_the_current_band(directory: DirectoryService) -> None:
    ravi = _find(directory, "Ravi")

    assert ravi.band is not None
    assert ravi.band.compa_ratio == Decimal("0.89")


def test_total_pay_is_converted_to_usd_at_the_active_rate(directory: DirectoryService) -> None:
    hannah = _find(directory, "Hannah")

    assert hannah.total_pay_usd == Money(89_100_00, "USD")


def test_part_time_pay_is_compared_to_the_band_at_fte(directory: DirectoryService) -> None:
    arjun = _find(directory, "Arjun")

    assert arjun.band is not None
    assert arjun.band.position is BandPosition.IN_BAND
    assert arjun.band.fte_equivalent_base == Money(lakh(22_00_000), "INR")


def test_contractor_has_no_band(directory: DirectoryService) -> None:
    rahul = _find(directory, "Rahul")

    assert rahul.band is not None
    assert rahul.band.position is BandPosition.NO_BAND


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        (BandPosition.BELOW, ["Marcus Johnson", "Neha Gupta"]),
        (BandPosition.IN_BAND, ["Arjun Mehta", "Hannah Clarke", "Ravi Kumar"]),
        (BandPosition.ABOVE, ["Vikram Singh"]),
        (BandPosition.NO_BAND, ["Rahul Das"]),
    ],
)
def test_band_position_filter_agrees_with_the_domain_comparison(
    directory: DirectoryService, position: BandPosition, expected: list[str]
) -> None:
    page = directory.list(EmployeeQuery(band_position=position))

    assert _names(page.items) == expected
    assert all(entry.band is not None and entry.band.position is position for entry in page.items)


def test_terminated_employees_are_excluded_by_default(directory: DirectoryService) -> None:
    default = directory.list(EmployeeQuery(page_size=100))
    leavers = directory.list(EmployeeQuery(statuses=(EmploymentStatus.TERMINATED,)))

    assert "Old Timer" not in _names(default.items)
    assert _names(leavers.items) == ["Old Timer"]


def test_employee_leaving_in_the_future_is_listed_until_their_last_day(
    session: Session, directory: DirectoryService
) -> None:
    neha = directory.list(EmployeeQuery(q="Neha")).items[0].record.id
    EmployeeService(session).terminate(neha, date(2026, 12, 31))

    on_last_day = directory.list(EmployeeQuery(q="Neha"), as_of=date(2026, 12, 31))
    day_after = directory.list(EmployeeQuery(q="Neha"), as_of=date(2027, 1, 1))
    leavers = directory.list(
        EmployeeQuery(statuses=(EmploymentStatus.TERMINATED,)), as_of=date(2027, 1, 1)
    )

    assert on_last_day.items[0].record.status is EmploymentStatus.ACTIVE
    assert day_after.items == ()
    assert "Neha Gupta" in _names(leavers.items)
    assert leavers.items[-1].record.status is EmploymentStatus.TERMINATED


def test_employee_without_a_package_is_listed_without_one(directory: DirectoryService) -> None:
    priya = _find(directory, "Priya")

    assert priya.record.current is None
    assert priya.record.role_title is None
    assert priya.band is None
    assert priya.total_pay_usd is None


def test_future_hire_shows_their_role_but_no_current_package(directory: DirectoryService) -> None:
    sneha = _find(directory, "Sneha")

    assert sneha.record.role_title == "Software Engineer"
    assert sneha.record.country_code == "IN"
    assert sneha.record.current is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (EmployeeQuery(country_code="DE"), ["Hannah Clarke"]),
        (EmployeeQuery(level=4), ["Vikram Singh"]),
        (EmployeeQuery(employment_types=(EmploymentType.PART_TIME,)), ["Arjun Mehta"]),
        (EmployeeQuery(q="emp-05"), ["Hannah Clarke", "Rahul Das"]),
    ],
)
def test_filters_narrow_the_list(
    directory: DirectoryService, query: EmployeeQuery, expected: list[str]
) -> None:
    page = directory.list(query)

    assert sorted(_names(page.items)) == sorted(expected)


def test_filters_by_department_and_role(directory: DirectoryService, reference: Reference) -> None:
    sales = directory.list(EmployeeQuery(department_id=reference.sales_id))
    senior = directory.list(EmployeeQuery(role_id=reference.se_l4_id))

    assert _names(sales.items) == ["Marcus Johnson"]
    assert _names(senior.items) == ["Vikram Singh"]


def test_search_matches_the_start_of_a_name_ignoring_case(directory: DirectoryService) -> None:
    assert _names(directory.list(EmployeeQuery(q="ravi")).items) == ["Ravi Kumar"]
    assert _names(directory.list(EmployeeQuery(q="kumar")).items) == []


def test_search_treats_wildcards_as_plain_text(directory: DirectoryService) -> None:
    assert directory.list(EmployeeQuery(q="%")).items == ()


def test_sorting_by_total_pay_compares_everyone_in_usd(directory: DirectoryService) -> None:
    page = directory.list(EmployeeQuery(sort=EmployeeSort.TOTAL_PAY_USD, descending=True))

    assert _names(page.items) == [
        "Hannah Clarke",
        "Marcus Johnson",
        "Vikram Singh",
        "Rahul Das",
        "Ravi Kumar",
        "Neha Gupta",
        "Arjun Mehta",
        "Sneha Patil",
        "Priya Nair",
    ]


def test_pages_report_the_total_and_return_the_requested_slice(
    directory: DirectoryService,
) -> None:
    page = directory.list(EmployeeQuery(page=2, page_size=3))

    assert page.total == 9
    assert (page.page, page.page_size) == (2, 3)
    assert _names(page.items) == ["Neha Gupta", "Priya Nair", "Rahul Das"]


@pytest.mark.parametrize(("page", "page_size"), [(0, 25), (1, 0), (1, 101)])
def test_page_outside_the_allowed_range_is_rejected(page: int, page_size: int) -> None:
    with pytest.raises(InvalidRequestError):
        EmployeeQuery(page=page, page_size=page_size)
