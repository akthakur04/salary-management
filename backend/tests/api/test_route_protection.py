"""Every route except login and health requires a session, checked over the whole route table.

The route table comes from the app's OpenAPI schema, which lists every path and
method the app serves. (FastAPI 0.16x mounts included routers lazily, so
`app.routes` no longer lists endpoints; the schema is the public, complete view.)
New endpoints are protected by default because they're mounted on the protected
router; this test fails if one is ever served without a session check.
"""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.main import PUBLIC_PATHS, create_app
from tests.conftest import BASE_URL, TODAY, make_test_settings

_SCHEMA = create_app(make_test_settings(), clock=FixedClock(TODAY)).openapi()
ROUTES = [(method.upper(), path) for path, item in _SCHEMA["paths"].items() for method in item]
PROTECTED = [(method, path) for method, path in ROUTES if path not in PUBLIC_PATHS]


def test_the_route_table_lists_every_public_and_protected_route() -> None:
    paths = {path for _, path in ROUTES}

    assert paths >= PUBLIC_PATHS
    assert len(PROTECTED) == len(ROUTES) - len(PUBLIC_PATHS)
    assert len(PROTECTED) >= 20


@pytest.mark.parametrize(("method", "path"), PROTECTED, ids=lambda value: str(value))
def test_every_route_except_login_and_health_rejects_a_request_without_a_session(
    app: FastAPI, method: str, path: str
) -> None:
    client = TestClient(app, base_url=BASE_URL)

    response = client.request(method, re.sub(r"\{[^}]+\}", "1", path))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_public_routes_answer_without_a_session(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    login = client.post("/api/v1/auth/login", json={"email": "x@acme.example", "password": "x"})

    assert health.status_code == 200
    assert login.json()["error"]["code"] == "INVALID_CREDENTIALS"
