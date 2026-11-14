"""The single HR login: an HttpOnly session cookie, enforced by FastAPI on every protected route."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.security import SESSION_COOKIE, create_session_token
from app.main import create_app
from tests.conftest import HR_EMAIL, HR_PASSWORD, SESSION_SECRET, make_test_settings

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
GENERIC_FAILURE = "That email and password don't match. Check both and try again."


def test_login_with_the_hr_credentials_sets_a_secure_session_cookie(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": HR_EMAIL, "password": HR_PASSWORD})

    assert response.status_code == 200
    assert response.json() == {"email": HR_EMAIL}
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Max-Age=28800", "Path=/"):
        assert attribute in cookie


def test_login_email_ignores_case_and_spaces(client: TestClient) -> None:
    response = client.post(
        LOGIN, json={"email": "  Meera.Iyer@ACME.example ", "password": HR_PASSWORD}
    )

    assert response.status_code == 200


def test_wrong_password_is_rejected_with_a_generic_message(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": HR_EMAIL, "password": "wrong"})

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "INVALID_CREDENTIALS", "message": GENERIC_FAILURE, "details": {}}
    }
    assert "set-cookie" not in response.headers


def test_unknown_email_gets_the_same_answer_as_a_wrong_password(client: TestClient) -> None:
    wrong_password = client.post(LOGIN, json={"email": HR_EMAIL, "password": "wrong"})
    unknown_email = client.post(LOGIN, json={"email": "who@acme.example", "password": "x"})

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_login_without_a_password_is_a_validation_error(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": HR_EMAIL})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_signed_in_user_can_see_who_they_are(signed_in: TestClient) -> None:
    response = signed_in.get(ME)

    assert response.status_code == 200
    assert response.json() == {"email": HR_EMAIL}


def test_request_without_a_session_is_rejected(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_expired_session_is_rejected(client: TestClient) -> None:
    nine_hours_ago = datetime.now(UTC) - timedelta(hours=9)
    token = create_session_token(
        HR_EMAIL, SESSION_SECRET, timedelta(hours=8), issued_at=nine_hours_ago
    )
    client.cookies.set(SESSION_COOKIE, token, domain="testserver")

    response = client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_tampered_session_is_rejected(signed_in: TestClient) -> None:
    token = signed_in.cookies[SESSION_COOKIE]
    header, payload, signature = token.split(".")
    tampered = ".".join([header, payload, signature[::-1]])
    signed_in.cookies.clear()
    signed_in.cookies.set(SESSION_COOKIE, tampered, domain="testserver")

    response = signed_in.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_signed_with_another_secret_is_rejected(client: TestClient) -> None:
    forged = create_session_token(HR_EMAIL, "an-attacker-secret-" + "z" * 40, timedelta(hours=8))
    client.cookies.set(SESSION_COOKIE, forged, domain="testserver")

    response = client.get(ME)

    assert response.status_code == 401


def test_logout_clears_the_session(signed_in: TestClient) -> None:
    response = signed_in.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert f'{SESSION_COOKIE}=""' in response.headers["set-cookie"]
    assert signed_in.get(ME).status_code == 401


@pytest.mark.parametrize(
    "missing",
    [
        {"hr_admin_email": ""},
        {"hr_admin_password_hash": SecretStr("")},
        {"hr_admin_password_hash": SecretStr("not-a-bcrypt-hash")},
        {"session_secret": SecretStr("too-short")},
    ],
)
def test_app_refuses_to_start_without_complete_auth_settings(missing: dict[str, object]) -> None:
    settings = make_test_settings().model_copy(update=missing)

    with pytest.raises(RuntimeError):
        create_app(settings)
