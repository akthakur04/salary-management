import csv
import io
from datetime import date
from decimal import Decimal

from app.domain.employment import EmploymentStatus, EmploymentType
from app.repositories.employees import EmployeeRecord
from app.services.csv_export import HEADERS, employees_csv
from app.services.directory import DirectoryEntry


def _record(name: str) -> EmployeeRecord:
    return EmployeeRecord(
        id=1,
        employee_code="EMP-00001",
        name=name,
        email="x@acme.example",
        employment_type=EmploymentType.FULL_TIME,
        fte=Decimal("1"),
        status=EmploymentStatus.ACTIVE,
        hire_date=date(2024, 1, 1),
        termination_date=None,
        role_id=None,
        role_title=None,
        level=None,
        department=None,
        country_code=None,
        country_name=None,
        current=None,
        band=None,
        usd_per_unit=None,
    )


def test_text_a_spreadsheet_would_run_as_a_formula_is_neutralised() -> None:
    output = employees_csv([DirectoryEntry(_record('=HYPERLINK("http://x")'), None, None)])

    (row,) = list(csv.DictReader(io.StringIO(output)))
    assert row["Name"] == '\'=HYPERLINK("http://x")'


def test_employee_without_a_package_has_empty_pay_columns() -> None:
    output = employees_csv([DirectoryEntry(_record("Priya Nair"), None, None)])

    (row,) = list(csv.DictReader(io.StringIO(output)))
    assert list(row) == list(HEADERS)
    assert (row["Base salary"], row["Band position"]) == ("", "")
