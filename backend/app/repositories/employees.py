"""Employees: lookups for the services, and the directory query.

The directory joins each employee to the compensation version in force on
`as_of`, and through it to the role, country, current pay band and active FX
rate. Role and country come from that version (or, for someone not yet started,
from their first version), so future-dated promotions and transfers apply on
their own date.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Row,
    Select,
    UnaryExpression,
    and_,
    case,
    func,
    literal,
    null,
    or_,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased

from app.domain.bands import BandPosition
from app.domain.bands import PayBand as DomainPayBand
from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.identity import EmployeeIdentity
from app.domain.money import Money
from app.domain.versions import ChangeReason
from app.models import CompensationVersion, Country, Department, Employee, FxRate, PayBand, Role
from app.repositories.pagination import Page, validate_page

CURRENT_EMPLOYEES = (EmploymentStatus.ACTIVE, EmploymentStatus.ON_LEAVE)


class EmployeeSort(StrEnum):
    NAME = "name"
    EMPLOYEE_CODE = "employee_code"
    BASE = "base"
    TOTAL_PAY_USD = "total_pay_usd"
    COMPA_RATIO = "compa_ratio"
    LAST_CHANGE = "last_change"


@dataclass(frozen=True, slots=True)
class EmployeeQuery:
    """Directory filters. Terminated employees are left out unless asked for (E11)."""

    q: str | None = None
    country_code: str | None = None
    department_id: int | None = None
    role_id: int | None = None
    level: int | None = None
    employment_types: tuple[EmploymentType, ...] = ()
    statuses: tuple[EmploymentStatus, ...] = CURRENT_EMPLOYEES
    band_position: BandPosition | None = None
    sort: EmployeeSort = EmployeeSort.NAME
    descending: bool = False
    page: int = 1
    page_size: int = 25

    def __post_init__(self) -> None:
        validate_page(self.page, self.page_size)


@dataclass(frozen=True, slots=True)
class CurrentPackage:
    version_id: int
    effective_from: date
    reason: ChangeReason
    currency: str
    base_annual_minor: int
    fixed_cash_minor: int
    target_variable_minor: int
    ttc_minor: int


@dataclass(frozen=True, slots=True)
class EmployeeRecord:
    """One directory row: the inputs the domain needs to compare pay and convert to USD."""

    id: int
    employee_code: str
    name: str
    email: str
    employment_type: EmploymentType
    fte: Decimal
    status: EmploymentStatus
    hire_date: date
    termination_date: date | None
    role_id: int | None
    role_title: str | None
    level: int | None
    department: str | None
    country_code: str | None
    country_name: str | None
    current: CurrentPackage | None
    band: DomainPayBand | None
    usd_per_unit: Decimal | None


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

    def list(self, query: EmployeeQuery, as_of: date) -> Page[EmployeeRecord]:
        directory = _Directory(as_of)
        filtered = directory.filtered(query)
        total = self._session.scalar(select(func.count()).select_from(filtered.subquery()))
        rows = self._session.execute(
            filtered.order_by(*directory.ordering(query))
            .limit(query.page_size)
            .offset((query.page - 1) * query.page_size)
        )
        return Page(
            items=tuple(directory.to_record(row) for row in rows),
            total=total or 0,
            page=query.page,
            page_size=query.page_size,
        )


class _Directory:
    """Builds the directory query for one `as_of` date."""

    def __init__(self, as_of: date) -> None:
        self.current = aliased(CompensationVersion, name="current_version")
        self.shown = aliased(CompensationVersion, name="shown_version")
        first = aliased(CompensationVersion, name="first_version")
        current = self.current

        first_version_id = (
            select(first.id)
            .where(first.employee_id == Employee.id)
            .order_by(first.effective_from, first.id)
            .limit(1)
            .correlate(Employee)
            .scalar_subquery()
        )
        self.base: Select[*tuple[Any, ...]] = (
            select(
                Employee,
                current,
                Role.title,
                Role.level,
                Department.name.label("department"),
                Country.code.label("country_code"),
                Country.name.label("country_name"),
                Country.currency.label("band_currency"),
                PayBand.min_minor,
                PayBand.mid_minor,
                PayBand.max_minor,
                FxRate.usd_per_unit,
                self.shown.role_id,
            )
            .select_from(Employee)
            .outerjoin(
                current,
                and_(
                    current.employee_id == Employee.id,
                    current.effective_from <= as_of,
                    or_(current.effective_to.is_(None), current.effective_to > as_of),
                ),
            )
            .outerjoin(self.shown, self.shown.id == func.coalesce(current.id, first_version_id))
            .outerjoin(Role, Role.id == self.shown.role_id)
            .outerjoin(Department, Department.id == Role.department_id)
            .outerjoin(Country, Country.code == self.shown.country_code)
            .outerjoin(
                PayBand,
                and_(
                    PayBand.role_id == self.shown.role_id,
                    PayBand.country_code == self.shown.country_code,
                ),
            )
            .outerjoin(FxRate, and_(FxRate.currency == current.currency, FxRate.is_active))
        )

    def band_position(self) -> ColumnElement[str | None]:
        """Same rule as the domain's compare_to_band, in SQL so it can filter and count.

        Comparing base with `band * FTE` is the FTE-equivalent comparison without dividing.
        """
        current = self.current
        return case(
            (current.id.is_(None), null()),
            (
                or_(Employee.employment_type == EmploymentType.CONTRACTOR, PayBand.id.is_(None)),
                literal(BandPosition.NO_BAND.value),
            ),
            (
                current.base_annual_minor < PayBand.min_minor * Employee.fte,
                literal(BandPosition.BELOW.value),
            ),
            (
                current.base_annual_minor > PayBand.max_minor * Employee.fte,
                literal(BandPosition.ABOVE.value),
            ),
            else_=literal(BandPosition.IN_BAND.value),
        )

    def filtered(self, query: EmployeeQuery) -> Select[*tuple[Any, ...]]:
        conditions: list[ColumnElement[bool]] = [Employee.status.in_(query.statuses)]
        if query.q:
            conditions.append(
                or_(
                    Employee.name.istartswith(query.q, autoescape=True),
                    Employee.employee_code.istartswith(query.q, autoescape=True),
                )
            )
        if query.country_code:
            conditions.append(self.shown.country_code == query.country_code)
        if query.department_id is not None:
            conditions.append(Role.department_id == query.department_id)
        if query.role_id is not None:
            conditions.append(self.shown.role_id == query.role_id)
        if query.level is not None:
            conditions.append(Role.level == query.level)
        if query.employment_types:
            conditions.append(Employee.employment_type.in_(query.employment_types))
        if query.band_position is not None:
            conditions.append(self.band_position() == query.band_position.value)
        return self.base.where(*conditions)

    def ordering(
        self, query: EmployeeQuery
    ) -> list[UnaryExpression[Any] | InstrumentedAttribute[int]]:
        current = self.current
        sort_columns: dict[EmployeeSort, ColumnElement[Any] | InstrumentedAttribute[Any]] = {
            EmployeeSort.NAME: Employee.name,
            EmployeeSort.EMPLOYEE_CODE: Employee.employee_code,
            EmployeeSort.BASE: current.base_annual_minor,
            EmployeeSort.TOTAL_PAY_USD: current.ttc_minor * FxRate.usd_per_unit,
            EmployeeSort.COMPA_RATIO: (current.base_annual_minor * 1.0)
            / (PayBand.mid_minor * Employee.fte),
            EmployeeSort.LAST_CHANGE: current.effective_from,
        }
        column = sort_columns[query.sort]
        direction = column.desc() if query.descending else column.asc()
        return [direction.nulls_last(), Employee.id]

    @staticmethod
    def to_record(row: Row[Any]) -> EmployeeRecord:
        (
            employee,
            current,
            role_title,
            level,
            department,
            country_code,
            country_name,
            band_currency,
            min_minor,
            mid_minor,
            max_minor,
            usd_per_unit,
            role_id,
        ) = tuple(row)
        band = (
            DomainPayBand(
                Money(min_minor, band_currency),
                Money(mid_minor, band_currency),
                Money(max_minor, band_currency),
            )
            if min_minor is not None
            else None
        )
        package = (
            CurrentPackage(
                version_id=current.id,
                effective_from=current.effective_from,
                reason=current.reason,
                currency=current.currency,
                base_annual_minor=current.base_annual_minor,
                fixed_cash_minor=current.fixed_cash_minor,
                target_variable_minor=current.target_variable_minor,
                ttc_minor=current.ttc_minor,
            )
            if current is not None
            else None
        )
        return EmployeeRecord(
            id=employee.id,
            employee_code=employee.employee_code,
            name=employee.name,
            email=employee.email,
            employment_type=employee.employment_type,
            fte=employee.fte,
            status=employee.status,
            hire_date=employee.hire_date,
            termination_date=employee.termination_date,
            role_id=role_id,
            role_title=role_title,
            level=level,
            department=department,
            country_code=country_code,
            country_name=country_name,
            current=package,
            band=band,
            usd_per_unit=usd_per_unit,
        )
