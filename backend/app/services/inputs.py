"""Plain inputs to the services. The API layer builds these from validated request bodies."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.components import ComponentBasis, ComponentType, Frequency
from app.domain.employment import EmploymentType
from app.domain.versions import ChangeReason


@dataclass(frozen=True, slots=True)
class ComponentInput:
    """One component, with its amount in the employee's local currency (minor units)."""

    type: ComponentType
    basis: ComponentBasis
    frequency: Frequency
    label: str
    amount_minor: int | None = None
    percent: Decimal | None = None
    payout_date: date | None = None


@dataclass(frozen=True, slots=True)
class HireRequest:
    """`components=None` means "use the role's defaults"."""

    employee_code: str
    name: str
    email: str
    country_code: str
    role_id: int
    employment_type: EmploymentType
    fte: Decimal
    hire_date: date
    base_annual_minor: int
    components: tuple[ComponentInput, ...] | None = None


@dataclass(frozen=True, slots=True)
class RevisionRequest:
    """A new compensation version.

    Role, country and components default to the latest version's. Carried-over
    components are the recurring ones only: a one-time payment belongs to the
    version it was recorded in.
    """

    effective_from: date
    reason: ChangeReason
    base_annual_minor: int
    role_id: int | None = None
    country_code: str | None = None
    components: tuple[ComponentInput, ...] | None = None
    note: str | None = None
