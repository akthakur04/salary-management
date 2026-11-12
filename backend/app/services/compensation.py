"""Use case: revise an employee's compensation (raise, promotion, transfer, correction)."""

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.domain.employment import EmploymentStatus
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.versions import CompensationChange, CompensationVersion, plan_revision
from app.repositories.compensation import CompensationRepository
from app.repositories.employees import EmployeeRepository
from app.repositories.reference import ReferenceRepository
from app.services.inputs import RevisionRequest
from app.services.lookups import (
    require_country_currency,
    require_employee,
    require_role,
    to_components,
)
from app.services.transactions import transaction


class CompensationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._employees = EmployeeRepository(session)
        self._compensation = CompensationRepository(session)
        self._reference = ReferenceRepository(session)

    def revise(self, employee_id: int, request: RevisionRequest) -> int:
        """Close the latest version and add the new one, in one transaction.

        Returns the new version's id.
        """
        employee = require_employee(self._employees, employee_id)
        if employee.status is EmploymentStatus.TERMINATED:
            raise ConflictError(
                "This employee is terminated, so their pay can't be changed.",
                code="EMPLOYEE_TERMINATED",
            )
        stored = self._compensation.history(employee_id)
        history = tuple(entry.version for entry in stored)
        latest = history[-1] if history else None

        change = self._change_from(request, latest)
        plan = plan_revision(history, change, change.package.currency)

        with transaction(self._session):
            if plan.closed_previous is not None:
                assert plan.closed_previous.effective_to is not None
                self._compensation.close(stored[-1].id, plan.closed_previous.effective_to)
            return self._compensation.add(employee_id, plan.new_version, request.note)

    def _change_from(
        self, request: RevisionRequest, latest: CompensationVersion | None
    ) -> CompensationChange:
        role_id = request.role_id or (latest.role_id if latest else None)
        country_code = request.country_code or (latest.country_code if latest else None)
        if role_id is None or country_code is None:
            raise ConflictError(
                "This employee has no compensation yet, so give the role and country.",
                code="ROLE_AND_COUNTRY_REQUIRED",
            )
        require_role(self._reference, role_id)
        currency = require_country_currency(self._reference, country_code)

        if request.components is not None:
            components = to_components(request.components, currency)
        elif latest is not None:
            components = tuple(c for c in latest.package.components if c.is_recurring)
        else:
            components = ()
        package = CompensationPackage(Money(request.base_annual_minor, currency), components)
        return CompensationChange(
            request.effective_from, request.reason, role_id, country_code, package
        )
