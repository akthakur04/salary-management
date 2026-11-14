from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.errors import ConflictError, NotFoundError
from app.domain.components import Component, ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.errors import CurrencyMismatchError, OverlappingVersionError
from app.domain.money import Money
from app.domain.versions import ChangeReason
from app.models import Employee
from app.repositories.compensation import CompensationRepository
from app.services.compensation import CompensationService
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
SIGN_ON = ComponentInput(
    ComponentType.ONE_TIME,
    ComponentBasis.FIXED_AMOUNT,
    Frequency.ONCE,
    "Sign-on bonus",
    amount_minor=lakh(1_50_000),
    payout_date=date(2022, 3, 14),
)
BONUS_10 = ComponentInput(
    ComponentType.BONUS,
    ComponentBasis.PERCENT_OF_BASE,
    Frequency.ANNUAL,
    "Annual bonus",
    percent=Decimal("10"),
)
BONUS_15 = ComponentInput(
    ComponentType.BONUS,
    ComponentBasis.PERCENT_OF_BASE,
    Frequency.ANNUAL,
    "Annual bonus",
    percent=Decimal("15"),
)


def _hire_ravi(session: Session, reference: Reference, clock: FixedClock) -> int:
    return EmployeeService(session, clock).hire(
        hire_request(reference, components=(HOUSING, BONUS_10, SIGN_ON))
    )


def _merit(effective_from: date, rupees: int) -> RevisionRequest:
    return RevisionRequest(effective_from, ChangeReason.MERIT, lakh(rupees))


def test_revision_closes_the_previous_version_and_adds_the_new_one(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)

    CompensationService(session).revise(employee_id, _merit(date(2023, 4, 1), 19_80_000))

    hire, merit = CompensationRepository(session).history(employee_id)
    assert hire.version.effective_to == date(2023, 4, 1)
    assert merit.version.effective_from == date(2023, 4, 1)
    assert merit.version.is_open
    assert merit.version.package.base_annual == Money(lakh(19_80_000), "INR")


def test_revision_keeps_recurring_components_but_not_one_time_payments(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)

    CompensationService(session).revise(employee_id, _merit(date(2023, 4, 1), 19_80_000))

    _, merit = CompensationRepository(session).history(employee_id)
    assert [c.label for c in merit.version.package.components] == [
        "Housing allowance",
        "Annual bonus",
    ]


def test_percentage_bonus_follows_the_new_base(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)

    CompensationService(session).revise(employee_id, _merit(date(2023, 4, 1), 20_00_000))

    _, merit = CompensationRepository(session).history(employee_id)
    assert merit.version.totals.target_variable == Money(lakh(2_00_000), "INR")


def test_note_is_saved_with_the_history(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    request = RevisionRequest(
        date(2023, 4, 1), ChangeReason.MERIT, lakh(19_80_000), note="2023 merit cycle"
    )

    CompensationService(session).revise(employee_id, request)

    _, merit = CompensationRepository(session).history(employee_id)
    assert merit.note == "2023 merit cycle"


def test_promotion_moves_the_employee_to_the_new_role(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    promotion = RevisionRequest(
        date(2027, 1, 1),
        ChangeReason.PROMOTION,
        lakh(26_88_000),
        role_id=reference.se_l4_id,
        components=(HOUSING, BONUS_15),
    )

    CompensationService(session).revise(employee_id, promotion)

    _, promoted = CompensationRepository(session).history(employee_id)
    assert promoted.version.role_id == reference.se_l4_id
    assert promoted.version.package.components[-1] == Component.bonus_percent(Decimal("15"))


def test_transfer_records_pay_in_the_new_country_currency(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = EmployeeService(session, clock).hire(hire_request(reference))
    transfer = RevisionRequest(
        date(2024, 6, 1),
        ChangeReason.TRANSFER,
        68_000_00,
        country_code="DE",
        components=(),
    )

    CompensationService(session).revise(employee_id, transfer)

    india, germany = CompensationRepository(session).history(employee_id)
    assert india.version.package.currency == "INR"
    assert (germany.version.country_code, germany.version.package.currency) == ("DE", "EUR")


def test_transfer_must_restate_fixed_amounts_in_the_new_currency(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    transfer = RevisionRequest(
        date(2024, 6, 1), ChangeReason.TRANSFER, 68_000_00, country_code="DE"
    )

    with pytest.raises(CurrencyMismatchError):
        CompensationService(session).revise(employee_id, transfer)


def test_correction_dated_between_two_versions_is_rejected_and_nothing_changes(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    service = CompensationService(session)
    service.revise(employee_id, _merit(date(2023, 4, 1), 19_80_000))
    before = CompensationRepository(session).history(employee_id)
    correction = RevisionRequest(date(2022, 10, 1), ChangeReason.CORRECTION, lakh(18_50_000))

    with pytest.raises(OverlappingVersionError):
        service.revise(employee_id, correction)

    assert CompensationRepository(session).history(employee_id) == before


def test_revision_is_all_or_nothing(
    session: Session, reference: Reference, clock: FixedClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    before = CompensationRepository(session).history(employee_id)

    def fail_to_add(*_: object, **__: object) -> int:
        raise RuntimeError("database went away")

    monkeypatch.setattr(CompensationRepository, "add", fail_to_add)
    with pytest.raises(RuntimeError):
        CompensationService(session).revise(employee_id, _merit(date(2023, 4, 1), 19_80_000))

    monkeypatch.undo()
    assert CompensationRepository(session).history(employee_id) == before


def test_revising_an_unknown_employee_is_rejected(session: Session, reference: Reference) -> None:
    with pytest.raises(NotFoundError) as raised:
        CompensationService(session).revise(999, _merit(date(2023, 4, 1), 19_80_000))

    assert raised.value.code == "EMPLOYEE_NOT_FOUND"


def test_change_after_the_last_day_of_employment_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    EmployeeService(session, clock).terminate(employee_id, date(2026, 10, 31))

    with pytest.raises(ConflictError) as raised:
        CompensationService(session).revise(employee_id, _merit(date(2026, 11, 1), 25_00_000))

    assert raised.value.code == "CHANGE_AFTER_TERMINATION"


def test_change_before_a_future_last_day_is_allowed(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    employee_id = _hire_ravi(session, reference, clock)
    EmployeeService(session, clock).terminate(employee_id, date(2027, 1, 31))

    CompensationService(session).revise(employee_id, _merit(date(2027, 1, 1), 25_00_000))

    assert len(CompensationRepository(session).history(employee_id)) == 2


def _employee_without_a_package(session: Session) -> int:
    employee = Employee(
        employee_code="EMP-02904",
        name="Priya Nair",
        email="priya@acme.example",
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal("1"),
        status=EmploymentStatus.ACTIVE,
        hire_date=date(2020, 1, 6),
    )
    session.add(employee)
    session.commit()
    return employee.id


def test_employee_without_a_package_gets_one_recorded_as_their_hire(
    session: Session, reference: Reference
) -> None:
    employee_id = _employee_without_a_package(session)
    first_package = RevisionRequest(
        date(2020, 1, 6),
        ChangeReason.HIRE,
        lakh(30_00_000),
        role_id=reference.se_l3_id,
        country_code="IN",
    )

    CompensationService(session).revise(employee_id, first_package)

    (stored,) = CompensationRepository(session).history(employee_id)
    assert stored.version.reason is ChangeReason.HIRE
    assert stored.version.package.components == ()


def test_first_package_needs_a_role_and_country(session: Session, reference: Reference) -> None:
    employee_id = _employee_without_a_package(session)
    missing_role = RevisionRequest(date(2020, 1, 6), ChangeReason.HIRE, lakh(30_00_000))

    with pytest.raises(ConflictError) as raised:
        CompensationService(session).revise(employee_id, missing_role)

    assert raised.value.code == "ROLE_AND_COUNTRY_REQUIRED"
