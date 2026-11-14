"""Employee endpoints: directory, CSV export, profile, history, hire, edit, terminate, revise."""

import csv
import io
from typing import Any

from fastapi.testclient import TestClient

from tests.api.conftest import money
from tests.integration.factories import Reference, lakh

EMPLOYEES = "/api/v1/employees"

# Directory -----------------------------------------------------------------------------


def test_directory_lists_current_employees_with_band_and_usd(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.get(EMPLOYEES)

    body = response.json()
    assert response.status_code == 200
    assert (body["total"], body["page"], body["page_size"]) == (4, 1, 25)
    ravi = next(item for item in body["items"] if item["name"] == "Ravi Kumar")
    assert ravi == {
        "id": company["ravi"],
        "employee_code": "EMP-04821",
        "name": "Ravi Kumar",
        "email": "ravi.kumar@acme.example",
        "role": {"id": ravi["role"]["id"], "title": "Software Engineer", "level": 3},
        "department": "Engineering",
        "country": {"code": "IN", "name": "India"},
        "employment_type": "full_time",
        "fte": "1.00",
        "status": "active",
        "base_salary": money(lakh(24_00_000)),
        "total_pay": money(lakh(30_26_400)),
        "total_pay_usd": money(36_316_80, "USD"),
        "band": {
            "position": "in_band",
            "compa_ratio": "0.89",
            "fte_equivalent_base": money(lakh(24_00_000)),
            "gap_to_minimum": None,
        },
        "last_change": "2025-04-01",
    }


def test_directory_filters_come_from_query_parameters(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    below = signed_in.get(EMPLOYEES, params={"band_position": "below"}).json()
    germany = signed_in.get(EMPLOYEES, params={"country": "DE"}).json()
    contractors = signed_in.get(EMPLOYEES, params={"employment_type": "contractor"}).json()

    assert [item["name"] for item in below["items"]] == ["Neha Gupta"]
    assert [item["name"] for item in germany["items"]] == ["Hannah Clarke"]
    assert [item["name"] for item in contractors["items"]] == ["Rahul Das"]
    assert contractors["items"][0]["band"]["position"] == "no_band"


def test_directory_sorts_by_total_pay_in_usd(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    body = signed_in.get(EMPLOYEES, params={"sort": "total_pay_usd", "order": "desc"}).json()

    assert [item["name"] for item in body["items"]] == [
        "Hannah Clarke",
        "Ravi Kumar",
        "Rahul Das",
        "Neha Gupta",
    ]


def test_directory_rejects_a_page_size_above_100(signed_in: TestClient) -> None:
    response = signed_in.get(EMPLOYEES, params={"page_size": 101})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_csv_export_matches_the_filters(signed_in: TestClient, company: dict[str, int]) -> None:
    response = signed_in.get(f"{EMPLOYEES}/export.csv", params={"country": "IN"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="employees-2026-11-12.csv"' in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["Name"] for row in rows] == ["Neha Gupta", "Rahul Das", "Ravi Kumar"]
    ravi = rows[2]
    assert ravi["Employee code"] == "EMP-04821"
    assert ravi["Currency"] == "INR"
    assert ravi["Base salary"] == "2400000.00"
    assert ravi["Total pay"] == "3026400.00"
    assert ravi["Total pay (USD)"] == "36316.80"
    assert ravi["Band position"] == "In band"
    assert ravi["Compa-ratio"] == "0.89"


# Profile and history -------------------------------------------------------------------


def test_profile_shows_package_band_peers_and_one_time_payments(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.get(f"{EMPLOYEES}/{company['ravi']}")

    profile = response.json()
    assert response.status_code == 200
    assert profile["name"] == "Ravi Kumar"
    assert profile["role"]["title"] == "Software Engineer"
    package = profile["package"]
    assert package["effective_from"] == "2025-04-01"
    assert package["base_salary"] == money(lakh(24_00_000))
    assert [c["label"] for c in package["components"]] == [
        "Housing allowance",
        "Meal allowance",
        "Annual bonus",
    ]
    assert package["components"][0]["annual_amount"] == money(lakh(3_60_000))
    assert package["fixed_cash"] == money(lakh(27_86_400))
    assert package["total_target_compensation"] == money(lakh(30_26_400))
    assert package["total_target_compensation_usd"] == money(36_316_80, "USD")
    assert package["variable_share"] == "7.9"
    assert profile["band"]["compa_ratio"] == "0.89"
    assert profile["band"]["band"]["midpoint"] == money(lakh(27_00_000))
    assert profile["peers"] == {"count": 2, "median_base": money(lakh(22_55_000))}
    assert profile["one_time_payments"] == [
        {"label": "Sign-on bonus", "amount": money(lakh(1_50_000)), "payout_date": "2022-03-14"}
    ]
    assert profile["pending_changes"] == []


def test_unknown_employee_is_a_404(signed_in: TestClient) -> None:
    response = signed_in.get(f"{EMPLOYEES}/9999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EMPLOYEE_NOT_FOUND"


def test_history_lists_versions_newest_first_with_raise_percentages(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    history = signed_in.get(f"{EMPLOYEES}/{company['ravi']}/compensation").json()

    assert [(entry["effective_from"], entry["state"]) for entry in history] == [
        ("2025-04-01", "current"),
        ("2022-03-14", "past"),
    ]
    assert history[0]["base_change_percent"] == "9.1"
    assert history[1]["base_change_percent"] is None
    assert history[0]["role"]["level"] == 3


# Writes --------------------------------------------------------------------------------


def _hire_body(reference: Reference, **overrides: Any) -> dict[str, Any]:
    body = {
        "employee_code": "EMP-09121",
        "name": "Sneha Patil",
        "email": "sneha@acme.example",
        "country_code": "IN",
        "role_id": reference.se_l3_id,
        "employment_type": "full_time",
        "fte": "1",
        "hire_date": "2026-07-08",
        "base_annual_minor": lakh(25_00_000),
    }
    body.update(overrides)
    return body


def test_hire_returns_the_new_profile_with_role_defaults(
    signed_in: TestClient, reference: Reference
) -> None:
    response = signed_in.post(EMPLOYEES, json=_hire_body(reference))

    assert response.status_code == 201
    profile = response.json()
    assert response.headers["location"] == f"{EMPLOYEES}/{profile['id']}"
    assert [c["percent"] for c in profile["package"]["components"]] == ["10.00"]


def test_hire_with_a_duplicate_code_is_a_conflict(
    signed_in: TestClient, reference: Reference, company: dict[str, int]
) -> None:
    response = signed_in.post(EMPLOYEES, json=_hire_body(reference, employee_code="EMP-04821"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_EMPLOYEE"


def test_hire_with_a_bonus_above_100_percent_is_rejected(
    signed_in: TestClient, reference: Reference
) -> None:
    bonus = {
        "type": "bonus",
        "basis": "percent_of_base",
        "frequency": "annual",
        "label": "Annual bonus",
        "percent": "150",
    }

    response = signed_in.post(EMPLOYEES, json=_hire_body(reference, components=[bonus]))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PERCENTAGE"


def test_details_can_be_edited_and_leave_recorded(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.patch(
        f"{EMPLOYEES}/{company['neha']}", json={"name": "Neha Gupta-Rao", "status": "on_leave"}
    )

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["status"]) == ("Neha Gupta-Rao", "on_leave")


def test_status_cannot_be_set_to_terminated_by_editing(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.patch(f"{EMPLOYEES}/{company['neha']}", json={"status": "terminated"})

    assert response.status_code == 422


def test_editing_to_another_employees_email_is_a_conflict(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.patch(
        f"{EMPLOYEES}/{company['neha']}", json={"email": "Ravi.Kumar@acme.example"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_EMPLOYEE"


def test_terminate_records_the_last_day(signed_in: TestClient, company: dict[str, int]) -> None:
    response = signed_in.post(
        f"{EMPLOYEES}/{company['neha']}/terminate", json={"termination_date": "2026-11-30"}
    )

    assert response.status_code == 200
    assert response.json()["termination_date"] == "2026-11-30"
    assert response.json()["status"] == "active"


def test_revision_is_saved_and_returned(signed_in: TestClient, company: dict[str, int]) -> None:
    response = signed_in.post(
        f"{EMPLOYEES}/{company['neha']}/compensation",
        json={
            "effective_from": "2027-01-01",
            "reason": "market_adjustment",
            "base_annual_minor": lakh(23_00_000),
            "note": "Brought to band minimum",
        },
    )

    assert response.status_code == 201
    entry = response.json()
    assert (entry["state"], entry["note"]) == ("pending", "Brought to band minimum")
    assert entry["base_change_percent"] == "9.0"


def test_revision_dated_before_the_latest_version_is_a_conflict(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.post(
        f"{EMPLOYEES}/{company['ravi']}/compensation",
        json={"effective_from": "2024-10-01", "reason": "correction", "base_annual_minor": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "OVERLAPPING_VERSION"


def test_preview_shows_the_promotion_lands_below_the_new_band_and_saves_nothing(
    signed_in: TestClient, company: dict[str, int], reference: Reference
) -> None:
    bonus_15 = {
        "type": "bonus",
        "basis": "percent_of_base",
        "frequency": "annual",
        "label": "Annual bonus",
        "percent": "15",
    }
    housing = {
        "type": "allowance",
        "basis": "fixed_amount",
        "frequency": "monthly",
        "label": "Housing allowance",
        "amount_minor": lakh(30_000),
    }
    meal = {**housing, "label": "Meal allowance", "amount_minor": lakh(2_200)}

    response = signed_in.post(
        f"{EMPLOYEES}/{company['ravi']}/compensation/preview",
        json={
            "effective_from": "2027-01-01",
            "reason": "promotion",
            "role_id": reference.se_l4_id,
            "base_annual_minor": lakh(26_88_000),
            "components": [housing, meal, bonus_15],
        },
    )

    preview = response.json()
    assert response.status_code == 200
    assert preview["before"]["base_salary"] == money(lakh(24_00_000))
    assert preview["before"]["band"]["position"] == "in_band"
    assert preview["after"]["role"]["level"] == 4
    assert preview["after"]["base_salary"] == money(lakh(26_88_000))
    assert preview["after"]["total_target_compensation"] == money(lakh(34_77_600))
    assert preview["after"]["band"]["position"] == "below"
    assert preview["after"]["band"]["gap_to_minimum"] == money(lakh(1_12_000))
    assert preview["base_change_percent"] == "12.0"
    assert preview["takes_effect_later"] is True
    history = signed_in.get(f"{EMPLOYEES}/{company['ravi']}/compensation").json()
    assert len(history) == 2


def test_preview_reports_rule_violations_like_a_save(
    signed_in: TestClient, company: dict[str, int]
) -> None:
    response = signed_in.post(
        f"{EMPLOYEES}/{company['ravi']}/compensation/preview",
        json={"effective_from": "2024-10-01", "reason": "merit", "base_annual_minor": 1},
    )

    assert response.status_code == 409
