from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.domain.bands import PayBand
from app.domain.components import Component, ComponentType, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.errors import InvalidFxRateError, MissingFxRateError
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.role_defaults import RoleDefaultComponent
from app.domain.versions import ChangeReason, CompensationVersion
from app.models import CompensationVersion as CompensationVersionRow
from app.models import Employee, FxRate
from app.repositories.compensation import CompensationRepository
from app.repositories.reference import ReferenceRepository
from tests.integration.factories import Reference, lakh


def _employee(session: Session) -> Employee:
    employee = Employee(
        employee_code="EMP-04821",
        name="Ravi Kumar",
        email="ravi.kumar@acme.example",
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal("1"),
        status=EmploymentStatus.ACTIVE,
        hire_date=date(2022, 3, 14),
    )
    session.add(employee)
    session.flush()
    return employee


def test_country_currency_is_looked_up_by_code(session: Session, reference: Reference) -> None:
    repository = ReferenceRepository(session)

    assert repository.country_currency("IN") == "INR"
    assert repository.country_currency("FR") is None


def test_pay_band_is_returned_as_a_domain_band(session: Session, reference: Reference) -> None:
    band = ReferenceRepository(session).pay_band(reference.se_l3_id, "IN")

    assert band == PayBand(
        Money(lakh(22_00_000), "INR"), Money(lakh(27_00_000), "INR"), Money(lakh(32_00_000), "INR")
    )


def test_missing_pay_band_is_none(session: Session, reference: Reference) -> None:
    assert ReferenceRepository(session).pay_band(reference.se_l4_id, "DE") is None


def test_role_defaults_are_returned_as_domain_templates(
    session: Session, reference: Reference
) -> None:
    defaults = ReferenceRepository(session).role_defaults(reference.se_l4_id)

    assert defaults == (RoleDefaultComponent(ComponentType.BONUS, Decimal("15"), "Annual bonus"),)


def test_active_fx_rates_ignore_inactive_rate_sets(session: Session, reference: Reference) -> None:
    rates = ReferenceRepository(session).active_fx_rates()

    assert rates.to_usd(Money(100_00, "INR")) == Money(1_20, "USD")


def test_active_fx_rates_fail_loudly_for_a_currency_without_a_rate(
    session: Session, reference: Reference
) -> None:
    rates = ReferenceRepository(session).active_fx_rates()

    with pytest.raises(MissingFxRateError):
        rates.to_usd(Money(100_00, "BRL"))


def test_two_active_rate_sets_are_rejected(session: Session, reference: Reference) -> None:
    session.execute(update(FxRate).where(FxRate.rate_set == "2025-ref").values(is_active=True))

    with pytest.raises(InvalidFxRateError):
        ReferenceRepository(session).active_fx_rates()


def test_compensation_history_round_trips_through_the_database(
    session: Session, reference: Reference
) -> None:
    employee = _employee(session)
    package = CompensationPackage(
        Money(lakh(24_00_000), "INR"),
        (
            Component.allowance("Housing allowance", Money(lakh(30_000), "INR"), Frequency.MONTHLY),
            Component.bonus_percent(Decimal("10")),
            Component.one_time("Sign-on bonus", Money(lakh(1_50_000), "INR"), date(2022, 3, 14)),
        ),
    )
    version = CompensationVersion(
        date(2022, 3, 14), ChangeReason.HIRE, reference.se_l3_id, "IN", package
    )
    repository = CompensationRepository(session)

    repository.add(employee.id, version, note="Offer letter 2022-117")
    (stored,) = repository.history(employee.id)

    assert stored.version == version
    assert stored.note == "Offer letter 2022-117"


def test_stored_version_keeps_its_local_currency_totals(
    session: Session, reference: Reference
) -> None:
    employee = _employee(session)
    package = CompensationPackage(
        Money(lakh(24_00_000), "INR"), (Component.bonus_percent(Decimal("10")),)
    )
    version = CompensationVersion(
        date(2022, 3, 14), ChangeReason.HIRE, reference.se_l3_id, "IN", package
    )
    repository = CompensationRepository(session)

    version_id = repository.add(employee.id, version)

    stored = session.get_one(CompensationVersionRow, version_id)
    assert (stored.fixed_cash_minor, stored.target_variable_minor, stored.ttc_minor) == (
        lakh(24_00_000),
        lakh(2_40_000),
        lakh(26_40_000),
    )


def test_closing_a_version_sets_only_its_end_date(session: Session, reference: Reference) -> None:
    employee = _employee(session)
    version = CompensationVersion(
        date(2022, 3, 14),
        ChangeReason.HIRE,
        reference.se_l3_id,
        "IN",
        CompensationPackage(Money(lakh(18_00_000), "INR")),
    )
    repository = CompensationRepository(session)
    version_id = repository.add(employee.id, version)

    repository.close(version_id, date(2023, 4, 1))

    (stored,) = repository.history(employee.id)
    assert stored.version.effective_to == date(2023, 4, 1)
    assert stored.version.package == version.package
