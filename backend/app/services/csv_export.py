"""CSV of a filtered employee list: the bridge back to Excel (S4).

Amounts are in major units with two decimals, so spreadsheets read them as
numbers. Text that a spreadsheet would run as a formula is neutralised.
"""

import csv
import io
from collections.abc import Iterable
from decimal import Decimal

from app.domain.bands import BandPosition
from app.domain.employment import EmploymentStatus, EmploymentType
from app.services.directory import DirectoryEntry

HEADERS = (
    "Employee code",
    "Name",
    "Email",
    "Department",
    "Role",
    "Level",
    "Country",
    "Employment type",
    "FTE",
    "Status",
    "Currency",
    "Base salary",
    "Total pay",
    "Total pay (USD)",
    "Band position",
    "Compa-ratio",
    "Last change",
)

_BAND_LABELS = {
    BandPosition.IN_BAND: "In band",
    BandPosition.BELOW: "Below band",
    BandPosition.ABOVE: "Above band",
    BandPosition.NO_BAND: "No band",
}
_TYPE_LABELS = {
    EmploymentType.FULL_TIME: "Full-time",
    EmploymentType.PART_TIME: "Part-time",
    EmploymentType.CONTRACTOR: "Contractor",
}
_STATUS_LABELS = {
    EmploymentStatus.ACTIVE: "Active",
    EmploymentStatus.ON_LEAVE: "On leave",
    EmploymentStatus.TERMINATED: "Terminated",
}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def employees_csv(entries: Iterable[DirectoryEntry]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADERS)
    for entry in entries:
        writer.writerow(_row(entry))
    return buffer.getvalue()


def _row(entry: DirectoryEntry) -> list[str]:
    record, package, band = entry.record, entry.record.current, entry.band
    return [
        _text(record.employee_code),
        _text(record.name),
        _text(record.email),
        _text(record.department or ""),
        _text(record.role_title or ""),
        str(record.level or ""),
        record.country_code or "",
        _TYPE_LABELS[record.employment_type],
        f"{record.fte:.2f}",
        _STATUS_LABELS[record.status],
        package.currency if package else "",
        _amount(package.base_annual_minor) if package else "",
        _amount(package.ttc_minor) if package else "",
        _amount(entry.total_pay_usd.amount_minor) if entry.total_pay_usd else "",
        _BAND_LABELS[band.position] if band else "",
        f"{band.compa_ratio:.2f}" if band and band.compa_ratio is not None else "",
        package.effective_from.isoformat() if package else "",
    ]


def _amount(amount_minor: int) -> str:
    return f"{Decimal(amount_minor) / 100:.2f}"


def _text(value: str) -> str:
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value
