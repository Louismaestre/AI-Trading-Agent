from fastapi.testclient import TestClient

from app.main import create_app

URL = "/api/v1/market/status"


def test_status_during_a_session() -> None:
    response = TestClient(create_app()).get(URL, params={"at": "2026-09-29T10:00:00+02:00"})

    assert response.status_code == 200
    assert response.json() == {
        "now": "2026-09-29T10:00:00+02:00",
        "is_open": True,
        "next_open": "2026-09-30T07:00:00Z",
        "last_close": "2026-09-28T15:30:00Z",
    }


def test_status_on_saturday_is_closed() -> None:
    response = TestClient(create_app()).get(URL, params={"at": "2026-10-03T10:00:00+02:00"})

    assert response.json()["is_open"] is False


def test_status_without_timezone_is_422() -> None:
    response = TestClient(create_app()).get(URL, params={"at": "2026-09-29T10:00:00"})

    assert response.status_code == 422
