from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.clock import FixedClock
from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.domain.employment import EmploymentStatus
from app.domain.versions import ChangeReason
from app.models import Employee
from app.repositories.compensation import CompensationRepository
from app.services.compensation import CompensationService
from app.services.employees import EmployeeService
from app.services.inputs import RevisionRequest
from tests.integration.factories import TODAY, Reference, hire_request, lakh


def test_termination_sets_status_and_date_and_keeps_the_history(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))

    service.terminate(employee_id, date(2026, 10, 31))

    employee = session.get_one(Employee, employee_id)
    assert employee.status is EmploymentStatus.TERMINATED
    assert employee.termination_date == date(2026, 10, 31)
    assert len(CompensationRepository(session).history(employee_id)) == 1


def test_termination_on_today_is_allowed(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))

    service.terminate(employee_id, TODAY)

    assert session.get_one(Employee, employee_id).termination_date == TODAY


def test_termination_before_the_hire_date_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))

    with pytest.raises(InvalidRequestError) as raised:
        service.terminate(employee_id, date(2022, 3, 13))

    assert raised.value.code == "INVALID_TERMINATION_DATE"


def test_termination_in_the_future_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))

    with pytest.raises(InvalidRequestError) as raised:
        service.terminate(employee_id, date(2026, 11, 13))

    assert raised.value.code == "INVALID_TERMINATION_DATE"


def test_terminating_with_a_change_due_after_the_date_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))
    raise_in_january = RevisionRequest(date(2027, 1, 1), ChangeReason.MERIT, lakh(20_00_000))
    CompensationService(session).revise(employee_id, raise_in_january)

    with pytest.raises(ConflictError) as raised:
        service.terminate(employee_id, TODAY)

    assert raised.value.code == "PENDING_CHANGE_AFTER_TERMINATION"
    assert raised.value.details == {"effective_from": "2027-01-01"}
    assert session.get_one(Employee, employee_id).status is EmploymentStatus.ACTIVE


def test_terminating_twice_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    service = EmployeeService(session, clock)
    employee_id = service.hire(hire_request(reference))
    service.terminate(employee_id, date(2026, 10, 31))

    with pytest.raises(ConflictError) as raised:
        service.terminate(employee_id, TODAY)

    assert raised.value.code == "EMPLOYEE_ALREADY_TERMINATED"


def test_terminating_an_unknown_employee_is_rejected(
    session: Session, reference: Reference, clock: FixedClock
) -> None:
    with pytest.raises(NotFoundError):
        EmployeeService(session, clock).terminate(999, TODAY)
