"""Insights: how the organisation pays people, computed at read time in USD at reference rates."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.employment import EmploymentStatus, EmploymentType
from app.domain.versions import ChangeReason
from app.models import Employee
from app.services.compensation import CompensationService
from app.services.employees import EmployeeService
from app.services.inputs import RevisionRequest
from tests.api.conftest import money
from tests.integration.factories import Reference, hire_request, lakh

INSIGHTS = "/api/v1/insights"


def _add_employee_without_a_package(db: Session) -> None:
    db.add(
        Employee(
            employee_code="EMP-02904",
            name="Priya Nair",
            email="priya@acme.example",
            employment_type=EmploymentType.FULL_TIME,
            fte=Decimal("1"),
            status=EmploymentStatus.ACTIVE,
            hire_date=date(2020, 1, 6),
        )
    )
    db.commit()


def test_summary_reports_the_overview_kpis(signed_in: TestClient, company: dict[str, int]) -> None:
    response = signed_in.get(f"{INSIGHTS}/summary")

    assert response.status_code == 200
    assert response.json() == {
        "as_of": "2026-11-12",
        "headcount": 4,
        "joiners_this_quarter": 0,
        "leavers_this_quarter": 0,
        "total_pay_usd": money(186_868_80, "USD"),
        "median_pay_usd": money(34_958_40, "USD"),
        "paid_within_band_percent": "66.7",
        "bonus_eligible_percent": "100.0",
        "variable_share_percent": "7.2",
        "employees_without_package": 0,
    }


def test_summary_counts_joiners_and_leavers_this_quarter(
    signed_in: TestClient, company: dict[str, int], db: Session, reference: Reference
) -> None:
    EmployeeService(db).hire(
        hire_request(
            reference,
            employee_code="EMP-09121",
            name="Sneha Patil",
            email="sneha@acme.example",
            hire_date=date(2026, 10, 5),
        )
    )
    EmployeeService(db).terminate(company["neha"], date(2026, 10, 31))

    summary = signed_in.get(f"{INSIGHTS}/summary").json()

    assert (summary["joiners_this_quarter"], summary["leavers_this_quarter"]) == (1, 1)
    assert summary["headcount"] == 4


def test_employee_without_a_package_counts_in_headcount_but_not_in_pay(
    signed_in: TestClient, company: dict[str, int], db: Session
) -> None:
    _add_employee_without_a_package(db)

    summary = signed_in.get(f"{INSIGHTS}/summary").json()

    assert summary["headcount"] == 5
    assert summary["employees_without_package"] == 1
    assert summary["median_pay_usd"] == money(34_958_40, "USD")


def test_breakdown_by_country_gives_the_range_and_median_in_usd(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    groups = signed_in.get(f"{INSIGHTS}/breakdown", params={"group_by": "country"}).json()

    assert [group["key"] for group in groups] == ["DE", "IN"]
    india = groups[1]
    assert india == {
        "key": "IN",
        "label": "India",
        "headcount": 3,
        "minimum": money(27_852_00, "USD"),
        "median": money(33_600_00, "USD"),
        "mean": money(32_589_60, "USD"),
        "maximum": money(36_316_80, "USD"),
        "variable_share_percent": "5.5",
    }


def test_breakdown_by_level_groups_contractors_separately(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    groups = signed_in.get(f"{INSIGHTS}/breakdown", params={"group_by": "level"}).json()

    assert {(g["key"], g["label"], g["headcount"]) for g in groups} == {
        ("L3", "L3", 3),
        ("contractor", "Contractors", 1),
    }


def test_breakdown_can_be_filtered(signed_in: TestClient, company: dict[str, int]) -> None:
    groups = signed_in.get(
        f"{INSIGHTS}/breakdown", params={"group_by": "department", "country": "DE"}
    ).json()

    assert [(g["label"], g["headcount"]) for g in groups] == [("Engineering", 1)]


def test_band_distribution_leaves_out_unbanded_staff(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    groups = signed_in.get(f"{INSIGHTS}/band-distribution").json()

    assert groups == [
        {
            "key": "Engineering",
            "label": "Engineering",
            "below": 1,
            "in_band": 2,
            "above": 0,
            "banded": 3,
            "in_band_percent": "66.7",
        }
    ]


def test_exceptions_count_below_band_due_soon_and_missing_packages(
    signed_in: TestClient, company: dict[str, int], db: Session
) -> None:
    CompensationService(db).revise(
        company["ravi"], RevisionRequest(date(2026, 12, 1), ChangeReason.MERIT, lakh(25_00_000))
    )
    CompensationService(db).revise(
        company["hannah"], RevisionRequest(date(2027, 6, 1), ChangeReason.MERIT, 80_000_00)
    )
    _add_employee_without_a_package(db)

    response = signed_in.get(f"{INSIGHTS}/exceptions", params={"type": "below"})

    body = response.json()
    assert body["counts"] == {"below": 1, "above": 0, "pending": 1, "missing": 1, "total": 3}
    assert body["total"] == 1
    (neha,) = body["items"]
    assert neha["name"] == "Neha Gupta"
    assert neha["base_salary"] == money(lakh(21_10_000))
    assert neha["band_minimum"] == money(lakh(22_00_000))
    assert neha["gap"] == money(lakh(90_000))
    assert neha["gap_percent"] == "-4.1"


def test_pending_exceptions_show_base_today_and_the_new_base(
    signed_in: TestClient, company: dict[str, int], db: Session
) -> None:
    CompensationService(db).revise(
        company["ravi"], RevisionRequest(date(2026, 12, 1), ChangeReason.MERIT, lakh(25_00_000))
    )

    body = signed_in.get(f"{INSIGHTS}/exceptions", params={"type": "pending"}).json()

    (ravi,) = body["items"]
    assert ravi["base_salary"] == money(lakh(24_00_000))
    assert ravi["new_base_salary"] == money(lakh(25_00_000))
    assert (ravi["effective_from"], ravi["reason"]) == ("2026-12-01", "merit")


def test_missing_package_exceptions_list_the_employee(
    signed_in: TestClient, company: dict[str, int], db: Session
) -> None:
    _add_employee_without_a_package(db)

    body = signed_in.get(f"{INSIGHTS}/exceptions", params={"type": "missing"}).json()

    assert [item["name"] for item in body["items"]] == ["Priya Nair"]
    assert body["items"][0]["base_salary"] is None


def test_recent_changes_show_the_latest_recorded_first(
    signed_in: TestClient, company: dict[str, int], db: Session
) -> None:
    CompensationService(db).revise(
        company["ravi"], RevisionRequest(date(2026, 12, 1), ChangeReason.MERIT, lakh(25_00_000))
    )

    changes = signed_in.get(f"{INSIGHTS}/recent-changes", params={"limit": 2}).json()

    assert [(c["name"], c["effective_from"], c["is_pending"]) for c in changes] == [
        ("Ravi Kumar", "2026-12-01", True),
        ("Ravi Kumar", "2025-04-01", False),
    ]
    assert changes[0]["base_change_percent"] == "4.2"
    assert changes[1]["role"]["title"] == "Software Engineer"


@pytest.mark.parametrize("path", ["breakdown", "band-distribution"])
def test_unknown_grouping_is_a_validation_error(signed_in: TestClient, path: str) -> None:
    response = signed_in.get(f"{INSIGHTS}/{path}", params={"group_by": "planet"})

    assert response.status_code == 422


def test_band_exceptions_are_sorted_largest_gap_first_with_signed_percentages(
    signed_in: TestClient, company: dict[str, int], db: Session, reference: Reference
) -> None:
    hire = EmployeeService(db).hire
    hire(
        hire_request(
            reference,
            employee_code="EMP-06630",
            name="Karthik Reddy",
            email="karthik@acme.example",
            base_annual_minor=lakh(20_00_000),
        )
    )
    hire(
        hire_request(
            reference,
            employee_code="EMP-07408",
            name="Vikram Singh",
            email="vikram@acme.example",
            role_id=reference.se_l4_id,
            base_annual_minor=lakh(39_80_000),
        )
    )

    below = signed_in.get(f"{INSIGHTS}/exceptions", params={"type": "below"}).json()
    above = signed_in.get(f"{INSIGHTS}/exceptions", params={"type": "above"}).json()

    assert [(i["name"], i["gap_percent"]) for i in below["items"]] == [
        ("Karthik Reddy", "-9.1"),
        ("Neha Gupta", "-4.1"),
    ]
    (vikram,) = above["items"]
    assert vikram["band_maximum"] == money(lakh(38_00_000))
    assert (vikram["gap"], vikram["gap_percent"]) == (money(lakh(1_80_000)), "4.7")
