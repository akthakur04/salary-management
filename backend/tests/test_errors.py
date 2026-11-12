"""Every error leaves the API in one shape: {"error": {"code", "message", "details"}}."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import NotFoundError


def _add_route_raising(app: FastAPI, error: Exception) -> None:
    def raise_error() -> None:
        raise error

    app.add_api_route("/api/v1/_test/raise", raise_error)


def test_app_error_is_returned_in_the_standard_error_shape(app: FastAPI) -> None:
    _add_route_raising(app, NotFoundError("Employee 42 was not found.", details={"id": 42}))
    client = TestClient(app)

    response = client.get("/api/v1/_test/raise")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Employee 42 was not found.",
            "details": {"id": 42},
        }
    }


def test_app_error_can_carry_a_more_specific_code(app: FastAPI) -> None:
    _add_route_raising(app, NotFoundError("No pay band.", code="PAY_BAND_NOT_FOUND"))
    client = TestClient(app)

    response = client.get("/api/v1/_test/raise")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAY_BAND_NOT_FOUND"
    assert response.json()["error"]["details"] == {}


def test_invalid_request_returns_422_naming_each_invalid_field(app: FastAPI) -> None:
    def get_page(page: int) -> dict[str, int]:
        return {"page": page}

    app.add_api_route("/api/v1/_test/items", get_page)
    client = TestClient(app)

    response = client.get("/api/v1/_test/items", params={"page": "first"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Some fields are missing or invalid."
    assert error["details"]["fields"] == [
        {
            "field": "page",
            "location": "query",
            "message": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]


def test_unknown_route_returns_404_in_the_standard_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Not Found", "details": {}}
    }


def test_wrong_method_returns_405_in_the_standard_error_shape(client: TestClient) -> None:
    response = client.delete("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_unexpected_error_returns_500_without_leaking_internals(app: FastAPI) -> None:
    _add_route_raising(app, RuntimeError("connection string with password=hunter2"))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/_test/raise")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Something went wrong on our side. Try again in a moment.",
            "details": {},
        }
    }
    assert "hunter2" not in response.text
