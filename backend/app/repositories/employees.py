"""Employees: lookups used by the services."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.identity import EmployeeIdentity
from app.models import Employee


class EmployeeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, employee_id: int) -> Employee | None:
        return self._session.get(Employee, employee_id)

    def add(self, employee: Employee) -> int:
        self._session.add(employee)
        self._session.flush()
        return employee.id

    def identities_matching(self, identity: EmployeeIdentity) -> list[EmployeeIdentity]:
        """Existing employees that share the code or email (stored normalised)."""
        rows = self._session.execute(
            select(Employee.employee_code, Employee.email).where(
                or_(
                    Employee.employee_code == identity.employee_code,
                    Employee.email == identity.email,
                )
            )
        )
        return [EmployeeIdentity(row.employee_code, row.email) for row in rows]
