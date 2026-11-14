"""Use cases: how the organisation pays people, as of a date.

Everything is computed at read time from the version in force on `as_of`, in USD
at the active reference rates. People without a package count in headcount but
are left out of pay figures (E13); contractors count in cost but not in band
figures (E10); terminated employees are left out (E11).
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.domain.bands import BandPosition
from app.domain.employment import EmploymentType
from app.domain.money import Money
from app.domain.stats import (
    BandDistribution,
    PaySummary,
    band_distribution,
    share_percent,
    summarise_pay,
)
from app.domain.versions import ChangeReason
from app.repositories.compensation import CompensationRepository
from app.repositories.employees import EmployeeQuery, EmployeeRepository
from app.repositories.insights import InsightsRepository
from app.repositories.pagination import Page, validate_page
from app.repositories.reference import ReferenceRepository
from app.services.directory import DirectoryEntry, DirectoryService
from app.services.views import RoleInfo, Views, change_percent

USD = "USD"


class GroupBy(StrEnum):
    COUNTRY = "country"
    DEPARTMENT = "department"
    LEVEL = "level"


class ExceptionType(StrEnum):
    BELOW = "below"
    ABOVE = "above"
    PENDING = "pending"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class Summary:
    as_of: date
    headcount: int
    joiners_this_quarter: int
    leavers_this_quarter: int
    total_pay_usd: Money
    median_pay_usd: Money | None
    paid_within_band_percent: Decimal | None
    bonus_eligible_percent: Decimal | None
    variable_share_percent: Decimal | None
    employees_without_package: int


@dataclass(frozen=True, slots=True)
class PayGroup:
    key: str
    label: str
    summary: PaySummary
    variable_share_percent: Decimal | None


@dataclass(frozen=True, slots=True)
class BandGroup:
    key: str
    label: str
    distribution: BandDistribution


@dataclass(frozen=True, slots=True)
class ExceptionItem:
    entry: DirectoryEntry
    new_base: Money | None = None
    effective_from: date | None = None
    reason: ChangeReason | None = None


@dataclass(frozen=True, slots=True)
class ExceptionCounts:
    below: int
    above: int
    pending: int
    missing: int

    @property
    def total(self) -> int:
        return self.below + self.above + self.pending + self.missing


@dataclass(frozen=True, slots=True)
class RecentChange:
    employee_id: int
    name: str
    role: RoleInfo
    country_code: str
    reason: ChangeReason
    effective_from: date
    is_pending: bool
    base_change_percent: Decimal | None


class InsightsService:
    def __init__(self, session: Session, clock: Clock, pending_window_days: int = 60) -> None:
        self._directory = DirectoryService(session, clock)
        self._insights = InsightsRepository(session)
        self._compensation = CompensationRepository(session)
        self._employees = EmployeeRepository(session)
        self._reference = ReferenceRepository(session)
        self._clock = clock
        self._window = pending_window_days

    def summary(self, as_of: date | None = None) -> Summary:
        day = as_of or self._clock.today()
        people = self._current_people(EmployeeQuery(), day)
        paid = [e for e in people if e.record.current is not None]
        banded = band_distribution(_banded_positions(paid))
        eligible = [e for e in paid if e.record.employment_type is not EmploymentType.CONTRACTOR]
        with_variable = [e for e in eligible if _variable_minor(e) > 0]
        median = summarise_pay(_usd_totals(paid))
        quarter_start = date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)
        return Summary(
            as_of=day,
            headcount=len(people),
            joiners_this_quarter=self._insights.joiners_between(quarter_start, day),
            leavers_this_quarter=self._insights.leavers_between(quarter_start, day),
            total_pay_usd=Money(sum(_usd_totals(paid)), USD),
            median_pay_usd=Money(median.median, USD) if median else None,
            paid_within_band_percent=share_percent(banded.in_band, banded.banded),
            bonus_eligible_percent=share_percent(len(with_variable), len(eligible)),
            variable_share_percent=_variable_share(paid),
            employees_without_package=len(people) - len(paid),
        )

    def breakdown(
        self, group_by: GroupBy, filters: EmployeeQuery, as_of: date | None = None
    ) -> list[PayGroup]:
        day = as_of or self._clock.today()
        paid = [e for e in self._current_people(filters, day) if e.record.current is not None]
        groups = []
        for (key, label), members in _grouped(paid, _key_function(group_by)).items():
            summary = summarise_pay(_usd_totals(members))
            assert summary is not None
            groups.append(PayGroup(key, label, summary, _variable_share(members)))
        return sorted(groups, key=lambda group: (-group.summary.median, group.label))

    def band_distribution(
        self, group_by: GroupBy, filters: EmployeeQuery, as_of: date | None = None
    ) -> list[BandGroup]:
        day = as_of or self._clock.today()
        paid = [e for e in self._current_people(filters, day) if e.record.current is not None]
        groups = [
            BandGroup(key, label, band_distribution(_banded_positions(members)))
            for (key, label), members in _grouped(paid, _key_function(group_by)).items()
        ]
        return sorted(
            (group for group in groups if group.distribution.banded),
            key=lambda group: (-group.distribution.banded, group.label),
        )

    def exceptions(
        self, kind: ExceptionType, page: int, page_size: int, as_of: date | None = None
    ) -> tuple[ExceptionCounts, Page[ExceptionItem]]:
        validate_page(page, page_size)
        day = as_of or self._clock.today()
        people = self._current_people(EmployeeQuery(), day)
        by_position = {
            position: sorted(
                (e for e in people if e.band and e.band.position is position),
                key=_largest_gap_first,
            )
            for position in (BandPosition.BELOW, BandPosition.ABOVE)
        }
        pending = self._pending(people, day)
        missing = [e for e in people if e.record.current is None and e.record.role_id is None]
        lists: dict[ExceptionType, list[ExceptionItem]] = {
            ExceptionType.BELOW: [ExceptionItem(e) for e in by_position[BandPosition.BELOW]],
            ExceptionType.ABOVE: [ExceptionItem(e) for e in by_position[BandPosition.ABOVE]],
            ExceptionType.PENDING: pending,
            ExceptionType.MISSING: [ExceptionItem(e) for e in missing],
        }
        counts = ExceptionCounts(
            below=len(lists[ExceptionType.BELOW]),
            above=len(lists[ExceptionType.ABOVE]),
            pending=len(pending),
            missing=len(missing),
        )
        chosen = lists[kind]
        start = (page - 1) * page_size
        return counts, Page(tuple(chosen[start : start + page_size]), len(chosen), page, page_size)

    def recent_changes(self, limit: int, as_of: date | None = None) -> list[RecentChange]:
        day = as_of or self._clock.today()
        views = Views(self._reference)
        changes = []
        for employee_id, version_id in self._insights.recent_change_ids(limit):
            stored = self._compensation.history(employee_id)
            index = next(i for i, item in enumerate(stored) if item.id == version_id)
            version = stored[index].version
            previous = stored[index - 1].version if index > 0 else None
            employee = self._employees.get_one(employee_id)
            changes.append(
                RecentChange(
                    employee_id=employee_id,
                    name=employee.name,
                    role=views.role(version.role_id),
                    country_code=version.country_code,
                    reason=version.reason,
                    effective_from=version.effective_from,
                    is_pending=version.effective_from > day,
                    base_change_percent=change_percent(previous, version),
                )
            )
        return changes

    def _current_people(self, filters: EmployeeQuery, day: date) -> list[DirectoryEntry]:
        """Current employees who have started by `day`, matching the filters."""
        return [e for e in self._directory.export(filters, day) if e.record.hire_date <= day]

    def _pending(self, people: list[DirectoryEntry], day: date) -> list[ExceptionItem]:
        by_employee = {entry.record.id: entry for entry in people}
        return [
            ExceptionItem(
                by_employee[change.employee_id],
                new_base=Money(change.base_annual_minor, change.currency),
                effective_from=change.effective_from,
                reason=change.reason,
            )
            for change in self._insights.changes_due(day, day + timedelta(days=self._window))
            if change.employee_id in by_employee
        ]


def _key_function(group_by: GroupBy) -> Callable[[DirectoryEntry], tuple[str, str]]:
    def country(entry: DirectoryEntry) -> tuple[str, str]:
        return entry.record.country_code or "", entry.record.country_name or ""

    def department(entry: DirectoryEntry) -> tuple[str, str]:
        name = entry.record.department or ""
        return name, name

    def level(entry: DirectoryEntry) -> tuple[str, str]:
        if entry.record.employment_type is EmploymentType.CONTRACTOR:
            return "contractor", "Contractors"
        return f"L{entry.record.level}", f"L{entry.record.level}"

    return {GroupBy.COUNTRY: country, GroupBy.DEPARTMENT: department, GroupBy.LEVEL: level}[
        group_by
    ]


def _grouped(
    entries: Iterable[DirectoryEntry], key: Callable[[DirectoryEntry], tuple[str, str]]
) -> dict[tuple[str, str], list[DirectoryEntry]]:
    groups: dict[tuple[str, str], list[DirectoryEntry]] = {}
    for entry in entries:
        groups.setdefault(key(entry), []).append(entry)
    return groups


def _usd_totals(entries: Iterable[DirectoryEntry]) -> list[int]:
    return [e.total_pay_usd.amount_minor for e in entries if e.total_pay_usd is not None]


def _variable_minor(entry: DirectoryEntry) -> int:
    package = entry.record.current
    return package.target_variable_minor if package else 0


def _variable_share(entries: list[DirectoryEntry]) -> Decimal | None:
    total = Decimal(sum(_usd_totals(entries)))
    variable = sum(
        (
            Decimal(_variable_minor(e)) * (e.record.usd_per_unit or 0)
            for e in entries
            if e.record.current is not None
        ),
        start=Decimal(0),
    )
    return share_percent(variable, total)


def _banded_positions(entries: Iterable[DirectoryEntry]) -> list[BandPosition]:
    return [e.band.position for e in entries if e.band is not None]


def _largest_gap_first(entry: DirectoryEntry) -> Decimal:
    assert entry.band is not None
    assert entry.record.band is not None
    equivalent = Decimal(entry.band.fte_equivalent_base.amount_minor)
    if entry.band.position is BandPosition.BELOW:
        minimum = Decimal(entry.record.band.minimum.amount_minor)
        return -(minimum - equivalent) / minimum
    maximum = Decimal(entry.record.band.maximum.amount_minor)
    return -(equivalent - maximum) / maximum
