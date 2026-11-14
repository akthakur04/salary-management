"""Use cases: an employee's profile and their compensation history, as of a date."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy.orm import Session

from app.domain.bands import fte_equivalent
from app.domain.employment import EmploymentStatus, status_on
from app.domain.money import Money
from app.domain.stats import summarise_pay
from app.domain.versions import CompensationVersion
from app.models import Country, Employee
from app.repositories.compensation import CompensationRepository, StoredVersion
from app.repositories.employees import EmployeeRepository
from app.repositories.reference import ReferenceRepository
from app.services.lookups import require_employee
from app.services.views import BandView, RoleInfo, VersionView, Views, change_percent


class VersionState(StrEnum):
    CURRENT = "current"
    PENDING = "pending"
    PAST = "past"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class OneTimePayment:
    label: str
    amount: Money
    payout_date: date


@dataclass(frozen=True, slots=True)
class Peers:
    count: int
    median_base: Money | None


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    version_id: int
    version: CompensationVersion
    state: VersionState
    role: RoleInfo
    base_change_percent: Decimal | None
    note: str | None


@dataclass(frozen=True, slots=True)
class EmployeeProfile:
    employee: Employee
    status: EmploymentStatus
    role: RoleInfo | None
    country: Country | None
    current: VersionView | None
    current_version_id: int | None
    band: BandView | None
    peers: Peers
    pending: tuple[HistoryEntry, ...]
    one_time_payments: tuple[OneTimePayment, ...]


class ProfileService:
    def __init__(self, session: Session) -> None:
        self._employees = EmployeeRepository(session)
        self._compensation = CompensationRepository(session)
        self._reference = ReferenceRepository(session)
        self._views = Views(self._reference)

    def get(self, employee_id: int, as_of: date) -> EmployeeProfile:
        employee = require_employee(self._employees, employee_id)
        stored = self._compensation.history(employee_id)
        current = next((s for s in stored if s.version.is_in_force_on(as_of)), None)
        # Before their start date, a future hire shows their first version's role and country.
        shown = current or (stored[0] if stored else None)

        current_view = self._views.version(employee, current.version) if current else None
        band = (
            current_view.band
            if current_view
            else self._views.band(employee, shown.version)
            if shown
            else None
        )
        return EmployeeProfile(
            employee=employee,
            status=status_on(employee.status, employee.termination_date, as_of),
            role=self._views.role(shown.version.role_id) if shown else None,
            country=self._reference.country(shown.version.country_code) if shown else None,
            current=current_view,
            current_version_id=current.id if current else None,
            band=band,
            peers=self._peers(shown.version, as_of) if shown else Peers(0, None),
            pending=tuple(
                e for e in self._entries(stored, as_of) if e.state is VersionState.PENDING
            ),
            one_time_payments=_one_time_payments(stored),
        )

    def history(self, employee_id: int, as_of: date) -> list[HistoryEntry]:
        """Newest first. Superseded versions (replaced by a same-day correction) stay visible."""
        require_employee(self._employees, employee_id)
        stored = self._compensation.history(employee_id)
        return list(reversed(self._entries(stored, as_of)))

    def entry(self, employee_id: int, version_id: int, as_of: date) -> HistoryEntry:
        return next(e for e in self.history(employee_id, as_of) if e.version_id == version_id)

    def _entries(self, stored: tuple[StoredVersion, ...], as_of: date) -> list[HistoryEntry]:
        entries = []
        previous: CompensationVersion | None = None
        for item in stored:
            version = item.version
            entries.append(
                HistoryEntry(
                    version_id=item.id,
                    version=version,
                    state=_state(version, as_of),
                    role=self._views.role(version.role_id),
                    base_change_percent=change_percent(previous, version),
                    note=item.note,
                )
            )
            previous = version
        return entries

    def _peers(self, version: CompensationVersion, as_of: date) -> Peers:
        bases = [
            fte_equivalent(Money(base, version.package.currency), fte).amount_minor
            for base, fte in self._employees.peer_bases(
                version.role_id, version.country_code, as_of
            )
        ]
        summary = summarise_pay(bases)
        median = Money(summary.median, version.package.currency) if summary else None
        return Peers(count=len(bases), median_base=median)


def _state(version: CompensationVersion, as_of: date) -> VersionState:
    if version.effective_to is not None and version.effective_to == version.effective_from:
        return VersionState.SUPERSEDED
    if version.effective_from > as_of:
        return VersionState.PENDING
    if version.is_in_force_on(as_of):
        return VersionState.CURRENT
    return VersionState.PAST


def _one_time_payments(stored: tuple[StoredVersion, ...]) -> tuple[OneTimePayment, ...]:
    payments = [
        OneTimePayment(component.label, component.amount, component.payout_date)
        for item in stored
        for component in item.version.package.components
        if not component.is_recurring
        and component.amount is not None
        and component.payout_date is not None
    ]
    return tuple(sorted(payments, key=lambda payment: payment.payout_date))
