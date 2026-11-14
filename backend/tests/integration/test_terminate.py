from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, InvalidRequestError, NotFoundError
from app.domain.employment import EmploymentStatus, status_on
from app.domain.versions import ChangeReason
from app.models import Employee
from app.repositories.compensation import CompensationRepository
from app.services.compensation import CompensationService
from app.services.employees import EmployeeService
from app.services.inputs import RevisionRequest
from tests.integration.factories import TODAY, Reference, hire_request, lakh


def _status(employee: Employee, as_of: date) -> EmploymentStatus:
    return status_on(employee.status, employee.termination_date, as_of)


def test_termination_records_the_last_day_and_keeps_the_history(
    session: Session, reference: Reference
) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))

    service.terminate(employee_id, date(2026, 10, 31))

    employee = session.get_one(Employee, employee_id)
    assert employee.termination_date == date(2026, 10, 31)
    assert _status(employee, TODAY) is EmploymentStatus.TERMINATED
    assert len(CompensationRepository(session).history(employee_id)) == 1


def test_termination_can_be_dated_in_the_future(session: Session, reference: Reference) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))

    service.terminate(employee_id, date(2027, 1, 31))

    employee = session.get_one(Employee, employee_id)
    assert _status(employee, TODAY) is EmploymentStatus.ACTIVE
    assert _status(employee, date(2027, 2, 1)) is EmploymentStatus.TERMINATED


def test_termination_before_the_hire_date_is_rejected(
    session: Session, reference: Reference
) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))

    with pytest.raises(InvalidRequestError) as raised:
        service.terminate(employee_id, date(2022, 3, 13))

    assert raised.value.code == "INVALID_TERMINATION_DATE"


def test_terminating_with_a_change_due_after_the_last_day_is_rejected(
    session: Session, reference: Reference
) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))
    raise_in_january = RevisionRequest(date(2027, 1, 1), ChangeReason.MERIT, lakh(20_00_000))
    CompensationService(session).revise(employee_id, raise_in_january)

    with pytest.raises(ConflictError) as raised:
        service.terminate(employee_id, TODAY)

    assert raised.value.code == "PENDING_CHANGE_AFTER_TERMINATION"
    assert raised.value.details == {"effective_from": "2027-01-01"}
    assert session.get_one(Employee, employee_id).termination_date is None


def test_termination_dated_on_or_after_a_pending_change_is_allowed(
    session: Session, reference: Reference
) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))
    raise_in_january = RevisionRequest(date(2027, 1, 1), ChangeReason.MERIT, lakh(20_00_000))
    CompensationService(session).revise(employee_id, raise_in_january)

    service.terminate(employee_id, date(2027, 1, 1))

    assert session.get_one(Employee, employee_id).termination_date == date(2027, 1, 1)


def test_terminating_twice_is_rejected(session: Session, reference: Reference) -> None:
    service = EmployeeService(session)
    employee_id = service.hire(hire_request(reference))
    service.terminate(employee_id, date(2027, 1, 31))

    with pytest.raises(ConflictError) as raised:
        service.terminate(employee_id, TODAY)

    assert raised.value.code == "EMPLOYEE_ALREADY_TERMINATED"


def test_terminating_an_unknown_employee_is_rejected(
    session: Session, reference: Reference
) -> None:
    with pytest.raises(NotFoundError):
        EmployeeService(session).terminate(999, TODAY)
