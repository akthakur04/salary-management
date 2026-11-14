from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import make_test_settings


def test_health_reports_ok_when_the_database_answers(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_unavailable_when_the_database_cannot_be_reached(tmp_path: Path) -> None:
    unreachable = tmp_path / "missing-directory" / "salary.db"
    app = create_app(make_test_settings(database_url=f"sqlite:///{unreachable}"))

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}
