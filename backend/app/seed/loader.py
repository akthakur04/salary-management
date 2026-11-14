"""Write the generated demo data set to the database in bulk.

Idempotent: if the database already has data, seeding does nothing unless
`reset=True`, which clears the seeded tables and loads the same data again, all
in one transaction. Ids are assigned by the database (read back with RETURNING),
so Postgres sequences stay in step with the rows for later inserts by the app.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.domain.fx import FxRates
from app.models import (
    CompensationComponent,
    CompensationVersion,
    Country,
    Department,
    Employee,
    FxRate,
    PayBand,
    Role,
    RoleDefaultComponent,
)
from app.repositories.compensation import component_values, version_values
from app.seed.generator import DEFAULT_RANDOM_SEED, SeedData, generate
from app.seed.reference_data import COUNTRIES, RATE_SET
from app.services.transactions import transaction

_SEEDED_TABLES_CHILD_FIRST = (
    CompensationComponent,
    CompensationVersion,
    Employee,
    PayBand,
    RoleDefaultComponent,
    Role,
    Department,
    FxRate,
    Country,
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    loaded: bool
    employees: int
    versions: int


def seed_database(
    session: Session,
    employees: int = 10_000,
    random_seed: int = DEFAULT_RANDOM_SEED,
    reset: bool = False,
) -> SeedResult:
    if _has_data(session) and not reset:
        return SeedResult(
            loaded=False,
            employees=_count(session, Employee),
            versions=_count(session, CompensationVersion),
        )

    data = generate(employees, random_seed)
    rates = FxRates({country.currency: country.usd_per_unit for country in COUNTRIES})
    rates.ensure_covers(
        version.package.currency for employee in data.employees for version in employee.versions
    )
    with transaction(session):
        for model in _SEEDED_TABLES_CHILD_FIRST:
            session.execute(delete(model))
        versions = _insert(session, data)
    return SeedResult(loaded=True, employees=len(data.employees), versions=versions)


def _has_data(session: Session) -> bool:
    return _count(session, Country) > 0 or _count(session, Employee) > 0


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _insert_returning_ids(
    session: Session, model: type[Any], rows: Sequence[dict[str, Any]]
) -> list[int]:
    if not rows:
        return []
    statement = insert(model).returning(model.id, sort_by_parameter_order=True)
    return list(session.scalars(statement, rows))


def _insert(session: Session, data: SeedData) -> int:
    session.execute(
        insert(Country),
        [{"code": c.code, "name": c.name, "currency": c.currency} for c in COUNTRIES],
    )
    session.execute(
        insert(FxRate),
        [
            {
                "rate_set": RATE_SET,
                "currency": c.currency,
                "usd_per_unit": c.usd_per_unit,
                "is_active": True,
            }
            for c in COUNTRIES
        ],
    )

    department_ids = dict(
        zip(
            (d.id for d in data.departments),
            _insert_returning_ids(
                session, Department, [{"name": d.name} for d in data.departments]
            ),
            strict=True,
        )
    )
    role_ids = dict(
        zip(
            (r.id for r in data.roles),
            _insert_returning_ids(
                session,
                Role,
                [
                    {
                        "department_id": department_ids[r.department_id],
                        "family": r.family,
                        "level": r.level,
                        "title": r.title,
                    }
                    for r in data.roles
                ],
            ),
            strict=True,
        )
    )
    session.execute(
        insert(RoleDefaultComponent),
        [
            {
                "role_id": role_ids[role_id],
                "type": default.type,
                "percent": default.percent,
                "label": default.label,
            }
            for role_id, default in data.role_defaults
        ],
    )
    session.execute(
        insert(PayBand),
        [
            {
                "role_id": role_ids[b.role_id],
                "country_code": b.country_code,
                "min_minor": b.band.minimum.amount_minor,
                "mid_minor": b.band.midpoint.amount_minor,
                "max_minor": b.band.maximum.amount_minor,
            }
            for b in data.bands
        ],
    )

    employee_ids = _insert_returning_ids(
        session,
        Employee,
        [
            {
                "employee_code": e.employee_code,
                "name": e.name,
                "email": e.email,
                "employment_type": e.employment_type,
                "fte": e.fte,
                "status": e.status,
                "hire_date": e.hire_date,
                "termination_date": e.termination_date,
            }
            for e in data.employees
        ],
    )

    versions = [
        (employee_id, version)
        for employee_id, employee in zip(employee_ids, data.employees, strict=True)
        for version in employee.versions
    ]
    version_ids = _insert_returning_ids(
        session,
        CompensationVersion,
        [
            {**version_values(employee_id, version), "role_id": role_ids[version.role_id]}
            for employee_id, version in versions
        ],
    )
    component_rows = [
        {**component_values(component), "version_id": version_id}
        for version_id, (_, version) in zip(version_ids, versions, strict=True)
        for component in version.package.components
    ]
    if component_rows:
        session.execute(insert(CompensationComponent), component_rows)
    return len(versions)
