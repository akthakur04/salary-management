from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.errors import DuplicateEmployeeError, InvalidFteError
from app.models import Employee
from app.repositories.employees import EmployeeRepository
from app.services.employees import EmployeeService
from app.services.inputs import DetailsUpdate
from tests.integration.factories import Reference, hire_request


def _hire(session: Session, reference: Reference, code: str, email: str) -> int:
    return EmployeeService(session).hire(hire_request(reference, employee_code=code, email=email))


def test_details_can_change_name_employment_and_leave(
    session: Session, reference: Reference
) -> None:
    employee_id = _hire(session, reference, "EMP-00001", "a@acme.example")

    EmployeeService(session).update_details(
        employee_id,
        DetailsUpdate(
            name=" Ravi K. ",
            employment_type=EmploymentType.PART_TIME,
            fte=Decimal("0.6"),
            status=EmploymentStatus.ON_LEAVE,
        ),
    )

    employee = session.get_one(Employee, employee_id)
    assert (employee.name, employee.employment_type, employee.fte, employee.status) == (
        "Ravi K.",
        EmploymentType.PART_TIME,
        Decimal("0.6"),
        EmploymentStatus.ON_LEAVE,
    )


def test_keeping_your_own_email_is_not_a_duplicate(session: Session, reference: Reference) -> None:
    employee_id = _hire(session, reference, "EMP-00001", "a@acme.example")

    EmployeeService(session).update_details(employee_id, DetailsUpdate(email="A@acme.example"))

    assert session.get_one(Employee, employee_id).email == "a@acme.example"


def test_status_cannot_be_set_to_terminated_by_editing(
    session: Session, reference: Reference
) -> None:
    employee_id = _hire(session, reference, "EMP-00001", "a@acme.example")

    with pytest.raises(InvalidRequestError) as raised:
        EmployeeService(session).update_details(
            employee_id, DetailsUpdate(status=EmploymentStatus.TERMINATED)
        )

    assert raised.value.code == "USE_TERMINATE"


def test_a_rejected_edit_leaves_no_half_made_change_behind(
    session: Session, reference: Reference
) -> None:
    employee_id = _hire(session, reference, "EMP-00001", "a@acme.example")

    with pytest.raises(InvalidFteError):
        EmployeeService(session).update_details(
            employee_id, DetailsUpdate(email="new@acme.example", fte=Decimal("0.5"))
        )
    _hire(session, reference, "EMP-00002", "b@acme.example")  # any later commit

    session.expire_all()
    assert session.get_one(Employee, employee_id).email == "a@acme.example"


def test_duplicate_email_that_slips_past_the_check_is_still_reported(
    session: Session, reference: Reference, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _hire(session, reference, "EMP-00001", "a@acme.example")
    _hire(session, reference, "EMP-00002", "b@acme.example")
    monkeypatch.setattr(EmployeeRepository, "identities_matching", lambda *_: [])

    with pytest.raises(DuplicateEmployeeError):
        EmployeeService(session).update_details(first, DetailsUpdate(email="b@acme.example"))
