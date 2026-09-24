import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import create_app
from app.models import Instrument
from tests.integration.conftest import alembic_config


def test_models_and_migrations_are_in_sync(migrated_engine: Engine) -> None:
    """Fails if a model changed without a matching migration."""
    command.check(alembic_config())


def test_insert_and_read_instrument(db_session: Session) -> None:
    db_session.add(Instrument(ticker="MC.PA", name="LVMH", isin="FR0000121014", sector="Luxe"))
    db_session.commit()

    instrument = db_session.scalar(select(Instrument).where(Instrument.ticker == "MC.PA"))

    assert instrument is not None
    assert instrument.currency == "EUR"
    assert instrument.created_at is not None


def test_ticker_must_be_unique(db_session: Session) -> None:
    db_session.add(Instrument(ticker="OR.PA", name="L'Oréal"))
    db_session.commit()

    db_session.add(Instrument(ticker="OR.PA", name="Doublon"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_health_reports_database_ok(db_session: Session) -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
