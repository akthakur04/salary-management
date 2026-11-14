"""Use case: the employee directory, with band position and USD computed at read time."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.domain.bands import BandComparison, compare_to_band
from app.domain.fx import FxRates
from app.domain.money import Money
from app.repositories.employees import EmployeeQuery, EmployeeRecord, EmployeeRepository
from app.repositories.pagination import Page
from app.repositories.reference import ReferenceRepository


@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    record: EmployeeRecord
    band: BandComparison | None
    total_pay_usd: Money | None


class DirectoryService:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._employees = EmployeeRepository(session)
        self._reference = ReferenceRepository(session)
        self._clock = clock

    def search(self, query: EmployeeQuery, as_of: date | None = None) -> Page[DirectoryEntry]:
        page = self._employees.search(query, as_of or self._clock.today())
        rates = self._reference.active_fx_rates()
        return Page(
            items=tuple(_entry(record, rates) for record in page.items),
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )

    def export(self, query: EmployeeQuery, as_of: date | None = None) -> list[DirectoryEntry]:
        """Every matching employee, ignoring paging, for CSV export."""
        records = self._employees.list_all(query, as_of or self._clock.today())
        rates = self._reference.active_fx_rates()
        return [_entry(record, rates) for record in records]


def _entry(record: EmployeeRecord, rates: FxRates) -> DirectoryEntry:
    """Band position and USD for one row, against the current band and active rates."""
    package = record.current
    if package is None:
        return DirectoryEntry(record, None, None)

    band = compare_to_band(
        Money(package.base_annual_minor, package.currency),
        record.fte,
        record.employment_type,
        record.band,
    )
    total_pay_usd = rates.to_usd(Money(package.ttc_minor, package.currency))
    return DirectoryEntry(record, band, total_pay_usd)
