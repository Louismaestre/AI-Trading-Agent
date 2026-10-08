import datetime
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.llm import FakeLLM
from app.main import create_app
from app.models import DailyPrice, Instrument, Replay, ReplayKind
from app.routers.experiments import get_experiment_service
from app.schemas.agents import AnalystDecision
from app.services.experiment_service import ExperimentService, UnknownExperimentError
from app.services.instrument_service import InstrumentService

START = datetime.date(2026, 9, 15)
END = datetime.date(2026, 9, 17)
CUTOFF = datetime.date(2025, 4, 1)
_HOLD = AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")


class _OneTicker(ExperimentService):
    def start(
        self,
        experiment_id: str,
        tickers: list[str] | None = None,
        repeats: int = 1,
    ) -> list[Replay]:
        return super().start(experiment_id, tickers or ["MC.PA"], repeats=repeats)

    def run(self, replay_id: int, tickers: list[str] | None = None) -> Replay:
        return super().run(replay_id, tickers or ["MC.PA"])


def _yaml(folder: Path) -> None:
    (folder / "e1.yaml").write_text(
        "\n".join(
            [
                "id: E1",
                "name: E1 technical",
                "question: technical only?",
                "start: 2026-09-15",
                "end: 2026-09-17",
                "decision_frequency: WEEKLY",
                "graph:",
                "  fundamental: false",
                "  sentiment: false",
                "  debate_rounds: 0",
                "  risk: false",
            ]
        ),
        encoding="utf-8",
    )


def _seed(session: Session) -> None:
    InstrumentService(session).sync_universe()
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == "MC.PA"))
    assert instrument is not None
    for day in (datetime.date(2026, 9, 14), START, datetime.date(2026, 9, 16), END):
        session.add(
            DailyPrice(
                instrument_id=instrument.id,
                date=day,
                open=Decimal("100"),
                high=Decimal("100"),
                low=Decimal("100"),
                close=Decimal("100"),
                volume=1000,
            )
        )
    session.commit()


def _service(db_session: Session, folder: Path) -> ExperimentService:
    _seed(db_session)
    return _OneTicker(
        db_session,
        directory=folder,
        llm=FakeLLM([_HOLD] * 5),
        knowledge_cutoff=CUTOFF,
        lookback_sessions=0,
    )


def test_start_stores_the_experiment_on_the_replay(db_session: Session, tmp_path: Path) -> None:
    _yaml(tmp_path)
    service = _service(db_session, tmp_path)

    started = service.start("E1")
    replay = service.run(started[0].id)

    assert replay.experiment_id == "E1"
    assert replay.batch_id is not None
    assert replay.repeat_index == 0
    assert replay.kind is ReplayKind.AGENTS
    assert replay.graph == {
        "fundamental": False,
        "sentiment": False,
        "debate_rounds": 0,
        "risk": False,
        "model": None,
    }
    assert replay.benchmark_replay_id is not None


def test_three_repeats_share_a_batch(db_session: Session, tmp_path: Path) -> None:
    _yaml(tmp_path)
    service = _service(db_session, tmp_path)

    started = service.start("E1", repeats=3)

    assert len(started) == 3
    assert len({row.batch_id for row in started}) == 1
    assert [row.repeat_index for row in started] == [0, 1, 2]
    assert started[0].graph is not None
    assert started[0].graph["temperature"] == 0.2
    assert started[0].graph["cache"] is False

    for row in started:
        service.run(row.id)

    agents = list(
        db_session.scalars(
            select(Replay).where(Replay.kind == ReplayKind.AGENTS).order_by(Replay.id)
        )
    )
    assert len(agents) == 3
    assert len({row.batch_id for row in agents}) == 1


def test_unknown_experiment_is_rejected(db_session: Session, tmp_path: Path) -> None:
    service = ExperimentService(db_session, directory=tmp_path)
    with pytest.raises(UnknownExperimentError):
        service.start("E9")


@pytest.fixture
def client(db_session: Session, tmp_path: Path) -> Iterator[TestClient]:
    _yaml(tmp_path)
    service = _service(db_session, tmp_path)
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_experiment_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client


def test_experiments_api_starts_three_repeats(client: TestClient) -> None:
    created = client.post("/api/v1/experiments/E1/replays?repeats=3")
    assert created.status_code == 201
    body = created.json()
    assert len(body["repeats"]) == 3
    assert {row["batch_id"] for row in body["repeats"]} == {body["batch_id"]}
    assert [row["repeat_index"] for row in body["repeats"]] == [0, 1, 2]
    assert all(row["status"] == "DONE" for row in body["repeats"])

    scored = client.get(f"/api/v1/replays/{body['repeats'][0]['id']}/significance")
    assert scored.status_code == 200
    assert scored.json()["batch"]["count"] == 3
    assert scored.json()["batch"]["replay_ids"] == [row["id"] for row in body["repeats"]]


def test_experiments_api_lists_and_starts(client: TestClient) -> None:
    listed = client.get("/api/v1/experiments")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "E1"

    created = client.post("/api/v1/experiments/E1/replays")
    assert created.status_code == 201
    body = created.json()
    assert len(body["repeats"]) == 1
    assert body["repeats"][0]["experiment_id"] == "E1"
    assert body["repeats"][0]["status"] == "DONE"
    assert body["repeats"][0]["batch_id"] == body["batch_id"]

    scored = client.get(f"/api/v1/replays/{body['repeats'][0]['id']}/significance")
    assert scored.status_code == 200
    assert scored.json()["replay_id"] == body["repeats"][0]["id"]
    assert scored.json()["batch"]["count"] == 1
