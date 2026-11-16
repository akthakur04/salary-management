"""Use case: revise an employee's compensation (raise, promotion, transfer, correction)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.domain.employment import EmploymentStatus
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.versions import (
    CompensationChange,
    CompensationVersion,
    RevisionPlan,
    plan_revision,
)
from app.models import Employee
from app.repositories.compensation import CompensationRepository, StoredVersion
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
from app.services.views import VersionView, Views, change_percent


@dataclass(frozen=True, slots=True)
class RevisionPreview:
    before: VersionView | None
    after: VersionView
    base_change_percent: Decimal | None
    takes_effect_later: bool


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
        _, stored, plan = self._plan(employee_id, request)
        with transaction(self._session):
            if plan.closed_previous is not None:
                assert plan.closed_previous.effective_to is not None
                self._compensation.close(stored[-1].id, plan.closed_previous.effective_to)
            return self._compensation.add(employee_id, plan.new_version, request.note)

    def preview(self, employee_id: int, request: RevisionRequest, as_of: date) -> RevisionPreview:
        """What `revise` would save, with band position and USD, without saving anything.

        Runs the same checks as `revise`, so a preview fails exactly when a save would.
        """
        employee, stored, plan = self._plan(employee_id, request)
        views = Views(self._reference)
        before = stored[-1].version if stored else None
        after = plan.new_version
        return RevisionPreview(
            before=views.version(employee, before) if before else None,
            after=views.version(employee, after),
            base_change_percent=change_percent(before, after),
            takes_effect_later=after.effective_from > as_of,
        )

    def _plan(
        self, employee_id: int, request: RevisionRequest
    ) -> tuple[Employee, tuple[StoredVersion, ...], RevisionPlan]:
        employee = require_employee(self._employees, employee_id)
        last_day = employee.termination_date
        if employee.status is EmploymentStatus.TERMINATED or (
            last_day is not None and request.effective_from > last_day
        ):
            raise ConflictError(
                "This change would start after the employee's last day.",
                code="CHANGE_AFTER_TERMINATION",
                details={"last_day": last_day.isoformat() if last_day else None},
            )
        stored = self._compensation.history(employee_id)
        history = tuple(entry.version for entry in stored)
        change = self._change_from(request, history[-1] if history else None)
        return employee, stored, plan_revision(history, change, change.package.currency)

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
