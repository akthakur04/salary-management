"""Shared lookups and input mapping for the services."""

from collections.abc import Iterable

from app.core.errors import NotFoundError
from app.domain.components import Component
from app.domain.money import Money
from app.models import Employee, Role
from app.repositories.employees import EmployeeRepository
from app.repositories.reference import ReferenceRepository
from app.services.inputs import ComponentInput


def require_employee(employees: EmployeeRepository, employee_id: int) -> Employee:
    employee = employees.get(employee_id)
    if employee is None:
        raise NotFoundError(
            "That employee doesn't exist.", code="EMPLOYEE_NOT_FOUND", details={"id": employee_id}
        )
    return employee


def require_role(reference: ReferenceRepository, role_id: int) -> Role:
    role = reference.role(role_id)
    if role is None:
        raise NotFoundError(
            "That role doesn't exist.", code="ROLE_NOT_FOUND", details={"role_id": role_id}
        )
    return role


def require_country_currency(reference: ReferenceRepository, country_code: str) -> str:
    currency = reference.country_currency(country_code)
    if currency is None:
        raise NotFoundError(
            "That country isn't set up.",
            code="COUNTRY_NOT_FOUND",
            details={"country_code": country_code},
        )
    return currency


def to_components(inputs: Iterable[ComponentInput], currency: str) -> tuple[Component, ...]:
    """Build domain components; amounts are in the employee's local currency."""
    return tuple(
        Component(
            type=item.type,
            basis=item.basis,
            frequency=item.frequency,
            label=item.label,
            amount=Money(item.amount_minor, currency) if item.amount_minor is not None else None,
            percent=item.percent,
            payout_date=item.payout_date,
        )
        for item in inputs
    )
