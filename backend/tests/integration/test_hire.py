from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.errors import NotFoundError
from app.domain.components import Component, ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.errors import DuplicateEmployeeError, InvalidFteError, InvalidPercentageError
from app.domain.money import Money
from app.domain.versions import ChangeReason
from app.models import Employee, RoleDefaultComponent
from app.repositories.compensation import CompensationRepository
from app.repositories.employees import EmployeeRepository
from app.services.employees import EmployeeService
from app.services.inputs import ComponentInput
from tests.integration.factories import Reference, hire_request, lakh

HOUSING = ComponentInput(
    ComponentType.ALLOWANCE,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.MONTHLY,
    "Housing allowance",
    amount_minor=lakh(30_000),
)


def test_hire_creates_the_employee_and_their_first_version(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = EmployeeService(session, clock).hire(hire_request(reference))

    employee = session.get_one(Employee, employee_id)
    (stored,) = CompensationRepository(session).history(employee_id)
    assert (employee.employee_code, employee.status) == ("EMP-04821", EmploymentStatus.ACTIVE)
    assert stored.version.reason is ChangeReason.HIRE
    assert stored.version.effective_from == date(2022, 3, 14)
    assert (stored.version.role_id, stored.version.country_code) == (reference.se_l3_id, "IN")
    assert stored.version.is_open


def test_new_hire_gets_the_role_default_components(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = EmployeeService(session, clock).hire(hire_request(reference))

    (stored,) = CompensationRepository(session).history(employee_id)
    assert stored.version.package.components == (Component.bonus_percent(Decimal("10")),)
    assert stored.version.totals.total_target_compensation == Money(lakh(19_80_000), "INR")


def test_role_default_changed_after_hire_does_not_change_the_hire(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = EmployeeService(session, clock).hire(hire_request(reference))

    session.execute(
        update(RoleDefaultComponent)
        .where(RoleDefaultComponent.role_id == reference.se_l3_id)
        .values(percent=Decimal("12"))
    )

    (stored,) = CompensationRepository(session).history(employee_id)
    assert stored.version.package.components == (Component.bonus_percent(Decimal("10")),)


def test_hire_with_explicit_components_replaces_the_role_defaults(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    bonus = ComponentInput(
        ComponentType.BONUS,
        ComponentBasis.PERCENT_OF_BASE,
        Frequency.ANNUAL,
        "Annual bonus",
        percent=Decimal("20"),
    )

    employee_id = EmployeeService(session, clock).hire(
        hire_request(reference, components=(HOUSING, bonus))
    )

    (stored,) = CompensationRepository(session).history(employee_id)
    totals = stored.version.totals
    assert totals.fixed_cash == Money(lakh(18_00_000 + 3_60_000), "INR")
    assert totals.target_variable == Money(lakh(3_60_000), "INR")


@pytest.mark.parametrize(
    ("code", "email"),
    [("emp-04821", "someone.else@acme.example"), ("EMP-09999", "RAVI.KUMAR@acme.example")],
)
def test_hire_rejects_a_duplicate_employee_code_or_email(
    session: Session, reference: Reference, clock: FixedClock, code: str, email: str
) -> None:
    service = EmployeeService(session, clock)
    service.hire(hire_request(reference))

    with pytest.raises(DuplicateEmployeeError):
        service.hire(hire_request(reference, employee_code=code, email=email))


def test_duplicate_that_slips_past_the_check_is_still_reported_as_a_duplicate(
    session: Session, reference: Reference, clock: FixedClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = EmployeeService(session, clock)
    service.hire(hire_request(reference))
    monkeypatch.setattr(EmployeeRepository, "identities_matching", lambda *_: [])

    with pytest.raises(DuplicateEmployeeError):
        service.hire(hire_request(reference))


def test_hire_stores_code_and_email_normalised(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = EmployeeService(session, clock).hire(
        hire_request(reference, employee_code=" emp-04821 ", email="Ravi.Kumar@ACME.example")
    )

    employee = session.get_one(Employee, employee_id)
    assert (employee.employee_code, employee.email) == ("EMP-04821", "ravi.kumar@acme.example")


def test_hire_into_an_unknown_role_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    with pytest.raises(NotFoundError) as raised:
        EmployeeService(session, clock).hire(hire_request(reference, role_id=999))

    assert raised.value.code == "ROLE_NOT_FOUND"


def test_hire_into_an_unknown_country_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    with pytest.raises(NotFoundError) as raised:
        EmployeeService(session, clock).hire(hire_request(reference, country_code="FR"))

    assert raised.value.code == "COUNTRY_NOT_FOUND"


def test_hire_rejects_fte_that_does_not_fit_the_employment_type(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    with pytest.raises(InvalidFteError):
        EmployeeService(session, clock).hire(
            hire_request(reference, employment_type=EmploymentType.PART_TIME, fte=Decimal("1"))
        )


def test_nothing_is_saved_when_a_hire_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    too_much = ComponentInput(
        ComponentType.BONUS,
        ComponentBasis.PERCENT_OF_BASE,
        Frequency.ANNUAL,
        "Annual bonus",
        percent=Decimal("150"),
    )

    with pytest.raises(InvalidPercentageError):
        EmployeeService(session, clock).hire(hire_request(reference, components=(too_much,)))

    assert session.scalar(select(func.count()).select_from(Employee)) == 0
