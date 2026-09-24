from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import build_engine
from app.main import create_app
from app.routers.health import get_health_service
from app.schemas.health import ComponentStatus, HealthResponse
from app.services.health_service import HealthService


class _StubHealthService:
    def __init__(self, status: ComponentStatus) -> None:
        self._status: ComponentStatus = status

    def check(self) -> HealthResponse:
        return HealthResponse(status=self._status, environment="test", database=self._status)


def _client_with_status(status: ComponentStatus) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_health_service] = lambda: _StubHealthService(status)
    return TestClient(app)


def test_health_returns_200_when_everything_is_ok() -> None:
    response = _client_with_status("ok").get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test", "database": "ok"}


def test_health_returns_503_when_database_fails() -> None:
    response = _client_with_status("error").get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["database"] == "error"


def test_service_reports_unreachable_database() -> None:
    # Nothing listens on port 1: the connection is refused immediately.
    engine = build_engine("postgresql+psycopg://base:base@127.0.0.1:1/base")
    with Session(engine) as session:
        health = HealthService(get_settings(), session).check()
    engine.dispose()

    assert health.status == "error"
    assert health.database == "error"
