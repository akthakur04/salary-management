from fastapi.testclient import TestClient

from tests.integration.factories import Reference, lakh


def test_countries_list_each_currency(signed_in: TestClient, reference: Reference) -> None:
    response = signed_in.get("/api/v1/reference/countries")

    assert response.status_code == 200
    assert response.json() == [
        {"code": "DE", "name": "Germany", "currency": "EUR"},
        {"code": "IN", "name": "India", "currency": "INR"},
        {"code": "US", "name": "United States", "currency": "USD"},
    ]


def test_departments_are_listed_by_name(signed_in: TestClient, reference: Reference) -> None:
    response = signed_in.get("/api/v1/reference/departments")

    assert [d["name"] for d in response.json()] == ["Engineering", "Sales"]


def test_roles_include_their_default_pay_structure(
    signed_in: TestClient, reference: Reference
) -> None:
    roles = signed_in.get("/api/v1/reference/roles").json()

    senior = next(role for role in roles if role["id"] == reference.se_l4_id)
    assert senior == {
        "id": reference.se_l4_id,
        "department_id": reference.engineering_id,
        "department": "Engineering",
        "family": "Software Engineer",
        "level": 4,
        "title": "Senior Software Engineer",
        "defaults": [{"type": "bonus", "percent": "15.00", "label": "Annual bonus"}],
    }


def test_pay_bands_can_be_filtered_by_role_and_country(
    signed_in: TestClient, reference: Reference
) -> None:
    response = signed_in.get(
        "/api/v1/reference/pay-bands", params={"role_id": reference.se_l3_id, "country": "IN"}
    )

    assert response.json() == [
        {
            "role_id": reference.se_l3_id,
            "country_code": "IN",
            "minimum": {"amount_minor": lakh(22_00_000), "currency": "INR"},
            "midpoint": {"amount_minor": lakh(27_00_000), "currency": "INR"},
            "maximum": {"amount_minor": lakh(32_00_000), "currency": "INR"},
        }
    ]
