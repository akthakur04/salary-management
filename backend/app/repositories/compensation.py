"""Compensation history, mapped between database rows and domain versions."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.components import Component
from app.domain.money import Money
from app.domain.package import CompensationPackage
from app.domain.versions import CompensationVersion
from app.models import CompensationComponent
from app.models import CompensationVersion as VersionRow


@dataclass(frozen=True, slots=True)
class StoredVersion:
    id: int
    version: CompensationVersion
    note: str | None


class CompensationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def history(self, employee_id: int) -> tuple[StoredVersion, ...]:
        rows = self._session.scalars(
            select(VersionRow)
            .where(VersionRow.employee_id == employee_id)
            .options(selectinload(VersionRow.components))
            .order_by(VersionRow.effective_from, VersionRow.id)
        )
        return tuple(StoredVersion(row.id, _to_domain(row), row.note) for row in rows)

    def add(self, employee_id: int, version: CompensationVersion, note: str | None = None) -> int:
        """Store a version with its local-currency totals, computed once by the domain."""
        totals = version.totals
        row = VersionRow(
            employee_id=employee_id,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
            reason=version.reason,
            role_id=version.role_id,
            country_code=version.country_code,
            currency=version.package.currency,
            base_annual_minor=version.package.base_annual.amount_minor,
            fixed_cash_minor=totals.fixed_cash.amount_minor,
            target_variable_minor=totals.target_variable.amount_minor,
            ttc_minor=totals.total_target_compensation.amount_minor,
            note=note,
            components=[_to_row(component) for component in version.package.components],
        )
        self._session.add(row)
        self._session.flush()
        return row.id

    def close(self, version_id: int, effective_to: date) -> None:
        """End a version when a later one supersedes it: the only change a stored version gets."""
        row = self._session.get_one(VersionRow, version_id)
        row.effective_to = effective_to
        self._session.flush()


def _to_row(component: Component) -> CompensationComponent:
    return CompensationComponent(
        type=component.type,
        basis=component.basis,
        frequency=component.frequency,
        label=component.label,
        amount_minor=component.amount.amount_minor if component.amount else None,
        percent=component.percent,
        payout_date=component.payout_date,
    )


def _to_domain(row: VersionRow) -> CompensationVersion:
    components = tuple(
        Component(
            type=component.type,
            basis=component.basis,
            frequency=component.frequency,
            label=component.label,
            amount=(
                Money(component.amount_minor, row.currency)
                if component.amount_minor is not None
                else None
            ),
            percent=component.percent,
            payout_date=component.payout_date,
        )
        for component in row.components
    )
    return CompensationVersion(
        effective_from=row.effective_from,
        reason=row.reason,
        role_id=row.role_id,
        country_code=row.country_code,
        package=CompensationPackage(Money(row.base_annual_minor, row.currency), components),
        effective_to=row.effective_to,
    )
