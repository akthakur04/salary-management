"""Use cases for employment: hire and terminate."""

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, InvalidRequestError
from app.domain.employment import EmploymentStatus, validate_fte
from app.domain.errors import DuplicateEmployeeError
from app.domain.identity import EmployeeIdentity, ensure_unique_identity
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.role_defaults import components_for_new_hire
from app.domain.versions import ChangeReason, CompensationChange, pending_changes, plan_revision
from app.models import Employee
from app.repositories.compensation import CompensationRepository
from app.repositories.employees import EmployeeRepository
from app.repositories.reference import ReferenceRepository
from app.services.inputs import HireRequest
from app.services.lookups import (
    require_country_currency,
    require_employee,
    require_role,
    to_components,
)
from app.services.transactions import transaction


class EmployeeService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._employees = EmployeeRepository(session)
        self._compensation = CompensationRepository(session)
        self._reference = ReferenceRepository(session)

    def hire(self, request: HireRequest) -> int:
        """Create the employee and their first compensation version, in one transaction.

        Without explicit components, the role's defaults are copied onto the hire.
        """
        identity = EmployeeIdentity(request.employee_code, request.email)
        ensure_unique_identity(identity, self._employees.identities_matching(identity))
        require_role(self._reference, request.role_id)
        currency = require_country_currency(self._reference, request.country_code)
        validate_fte(request.employment_type, request.fte)

        components = (
            components_for_new_hire(self._reference.role_defaults(request.role_id))
            if request.components is None
            else to_components(request.components, currency)
        )
        change = CompensationChange(
            request.hire_date,
            ChangeReason.HIRE,
            request.role_id,
            request.country_code,
            CompensationPackage(Money(request.base_annual_minor, currency), components),
        )
        plan = plan_revision((), change, currency)

        try:
            with transaction(self._session):
                employee_id = self._employees.add(
                    Employee(
                        employee_code=identity.employee_code,
                        name=request.name.strip(),
                        email=identity.email,
                        employment_type=request.employment_type,
                        fte=request.fte,
                        status=EmploymentStatus.ACTIVE,
                        hire_date=request.hire_date,
                    )
                )
                self._compensation.add(employee_id, plan.new_version)
        except IntegrityError as error:
            raise DuplicateEmployeeError(
                "Another employee already has this employee code or email."
            ) from error
        return employee_id

    def terminate(self, employee_id: int, termination_date: date) -> None:
        """Record the last day of employment. The record and its salary history are kept.

        The date may be in the future: the employee counts as terminated from the
        day after it (see `status_on`), so no job has to flip a status later.
        """
        employee = require_employee(self._employees, employee_id)
        if employee.termination_date is not None or (
            employee.status is EmploymentStatus.TERMINATED
        ):
            raise ConflictError(
                "This employee already has a termination date.",
                code="EMPLOYEE_ALREADY_TERMINATED",
            )
        if termination_date < employee.hire_date:
            raise InvalidRequestError(
                "The last day of employment can't be before the hire date.",
                code="INVALID_TERMINATION_DATE",
                details={
                    "termination_date": termination_date.isoformat(),
                    "hire_date": employee.hire_date.isoformat(),
                },
            )
        history = [stored.version for stored in self._compensation.history(employee_id)]
        later = pending_changes(history, termination_date)
        if later:
            raise ConflictError(
                "A saved pay change takes effect after this last day. "
                "Choose a last day on or after the change.",
                code="PENDING_CHANGE_AFTER_TERMINATION",
                details={"effective_from": later[0].effective_from.isoformat()},
            )

        with transaction(self._session):
            employee.termination_date = termination_date
