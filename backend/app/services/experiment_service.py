"""Load the experiment matrix and start one replay with that graph."""

import datetime
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.llm import StructuredLLM
from app.models import Replay
from app.schemas.experiments import ExperimentConfig, ExperimentGraph
from app.services.agent_service import AgentService, build_agent_service
from app.services.replay_service import ReplayService

EXPERIMENTS_DIR = Path(__file__).resolve().parents[2] / "config" / "experiments"


class UnknownExperimentError(LookupError):
    """No YAML file exists for this experiment id."""


class DuplicateExperimentIdError(ValueError):
    """Two YAML files share the same id."""


def load_experiments(directory: Path | None = None) -> list[ExperimentConfig]:
    folder = directory or EXPERIMENTS_DIR
    found: list[ExperimentConfig] = []
    seen: set[str] = set()
    for path in sorted(folder.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = ExperimentConfig.model_validate(raw)
        if config.id in seen:
            raise DuplicateExperimentIdError(config.id)
        seen.add(config.id)
        found.append(config)
    return found


class ExperimentService:
    def __init__(
        self,
        session: Session,
        *,
        directory: Path | None = None,
        llm: StructuredLLM | None = None,
        agents: AgentService | None = None,
        lookback_sessions: int | None = None,
        knowledge_cutoff: datetime.date | None = None,
    ) -> None:
        self._session = session
        self._directory = directory or EXPERIMENTS_DIR
        self._llm = llm
        self._agents = agents
        self._lookback_sessions = lookback_sessions
        self._knowledge_cutoff = knowledge_cutoff

    def list_all(self) -> list[ExperimentConfig]:
        return load_experiments(self._directory)

    def get(self, experiment_id: str) -> ExperimentConfig:
        for config in self.list_all():
            if config.id == experiment_id:
                return config
        raise UnknownExperimentError(experiment_id)

    def start(self, experiment_id: str, tickers: list[str] | None = None) -> Replay:
        config = self.get(experiment_id)
        agents = self._agents or build_agent_service(
            self._session,
            config.graph.to_graph_config(),
            llm=self._llm,
            model=config.graph.model,
        )
        replays = ReplayService(
            self._session,
            agents=agents,
            knowledge_cutoff=self._knowledge_cutoff,
            lookback_sessions=self._lookback_sessions,
        )
        return replays.start(
            name=config.name,
            initial_capital=config.initial_capital,
            start=config.start,
            end=config.end,
            tickers=tickers,
            decision_frequency=config.decision_frequency,
            experiment_id=config.id,
            graph=config.graph.model_dump(),
        )

    def run(self, replay_id: int, tickers: list[str] | None = None) -> Replay:
        """Run with the injected test LLM, or let ReplayService rebuild from `graph`."""
        replay = ReplayService(self._session).get(replay_id)
        agents = self._agents
        if agents is None and self._llm is not None:
            stored = ExperimentGraph.model_validate(replay.graph or {})
            agents = build_agent_service(
                self._session, stored.to_graph_config(), llm=self._llm, model=stored.model
            )
        return ReplayService(
            self._session,
            agents=agents,
            knowledge_cutoff=self._knowledge_cutoff,
            lookback_sessions=self._lookback_sessions,
        ).run(replay_id, tickers)
