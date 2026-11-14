"""Constraints the database enforces on its own, behind the domain and service checks."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.versions import ChangeReason
from app.models import CompensationVersion, Employee, FxRate, PayBand
from tests.integration.factories import Reference


def _employee(code: str = "EMP-00001", email: str = "a@acme.example") -> Employee:
    return Employee(
        employee_code=code,
        name="Test Person",
        email=email,
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal("1"),
        status=EmploymentStatus.ACTIVE,
        hire_date=date(2024, 1, 1),
    )


def _version(
    employee_id: int,
    role_id: int,
    effective_from: date,
    effective_to: date | None = None,
) -> CompensationVersion:
    return CompensationVersion(
        employee_id=employee_id,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=ChangeReason.HIRE,
        role_id=role_id,
        country_code="IN",
        currency="INR",
        base_annual_minor=100,
        fixed_cash_minor=100,
        target_variable_minor=0,
        ttc_minor=100,
    )


def test_database_allows_only_one_open_version_per_employee(
    session: Session, reference: Reference
) -> None:
    employee = _employee()
    session.add(employee)
    session.flush()
    session.add(_version(employee.id, reference.se_l3_id, date(2024, 1, 1)))
    session.flush()

    session.add(_version(employee.id, reference.se_l3_id, date(2025, 1, 1)))
    with pytest.raises(IntegrityError):
        session.flush()


def test_closed_versions_do_not_count_as_open(session: Session, reference: Reference) -> None:
    employee = _employee()
    session.add(employee)
    session.flush()

    session.add_all(
        [
            _version(employee.id, reference.se_l3_id, date(2024, 1, 1), date(2025, 1, 1)),
            _version(employee.id, reference.se_l3_id, date(2025, 1, 1)),
        ]
    )
    session.flush()


@pytest.mark.parametrize(
    ("second_code", "second_email"),
    [("EMP-00001", "b@acme.example"), ("EMP-00002", "a@acme.example")],
)
def test_database_rejects_a_duplicate_employee_code_or_email(
    session: Session, second_code: str, second_email: str
) -> None:
    session.add(_employee())
    session.flush()

    session.add(_employee(second_code, second_email))
    with pytest.raises(IntegrityError):
        session.flush()


def test_database_rejects_a_version_that_ends_before_it_starts(
    session: Session, reference: Reference
) -> None:
    employee = _employee()
    session.add(employee)
    session.flush()

    session.add(_version(employee.id, reference.se_l3_id, date(2025, 1, 1), date(2024, 1, 1)))
    with pytest.raises(IntegrityError):
        session.flush()


def test_database_rejects_a_second_band_for_the_same_role_and_country(
    session: Session, reference: Reference
) -> None:
    session.add(
        PayBand(
            role_id=reference.se_l3_id,
            country_code="IN",
            min_minor=1,
            mid_minor=2,
            max_minor=3,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_fx_rates_read_back_exactly(session: Session, reference: Reference) -> None:
    rate = session.scalars(
        select(FxRate.usd_per_unit).where(FxRate.currency == "INR", FxRate.is_active)
    ).one()

    assert rate == Decimal("0.012")
