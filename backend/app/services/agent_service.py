"""Runs the agent graph on each tradable ticker and stores the decisions."""

import datetime
import time
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.agents.graph import GraphConfig, build_graph
from app.agents.tools import AgentTools
from app.config import get_settings
from app.indicators import technical_summary
from app.llm import OllamaLLM, StructuredLLM
from app.market_clock import ensure_aware, session_open
from app.models import AgentAction, AgentDecision, Instrument
from app.schemas.agents import AnalystReport, DebateArgument, RiskAssessment
from app.services.fundamentals_service import FundamentalsService
from app.services.market_data_service import MarketDataService, UnknownTickerError
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService
from app.services.risk_service import RiskService
from app.universe import tradable_tickers

HISTORY_LIMIT = 80


class UnknownDecisionError(LookupError):
    """No agent decision exists for this id."""


class AgentService:
    def __init__(
        self,
        session: Session,
        llm: StructuredLLM | None = None,
        graph_config: GraphConfig | None = None,
    ) -> None:
        self._session = session
        self._portfolios = PortfolioService(session)
        self._market = MarketDataService(session)
        self._fundamentals = FundamentalsService(session)
        self._news = NewsService(session)
        self._risk = RiskService(session, self._portfolios, self._market)
        self._llm = llm or OllamaLLM()
        self._graph_config = graph_config or GraphConfig(
            debate_rounds=0 if llm is not None else 2,
            risk=llm is None,
        )

    def run_agents(
        self,
        portfolio_id: int,
        as_of: datetime.date | datetime.datetime,
        tickers: Sequence[str] | None = None,
    ) -> list[AgentDecision]:
        """Invoke the graph once per ticker and persist each analyst decision."""
        self._portfolios.get(portfolio_id)
        if isinstance(as_of, datetime.datetime):
            moment = ensure_aware(as_of)
            day = moment.date()
        else:
            moment = _as_of_datetime(as_of)
            day = as_of
        tools = AgentTools(
            self._portfolios,
            self._market,
            portfolio_id,
            moment,
            self._fundamentals,
            self._news,
            self._risk,
        )
        graph = cast(Any, build_graph(self._llm, tools, self._graph_config))
        saved: list[AgentDecision] = []
        for ticker in tickers or tradable_tickers():
            record = self._run_one(graph, tools, portfolio_id, ticker, day, moment)
            if record is not None:
                saved.append(record)
        return saved

    def list_decisions(self, portfolio_id: int) -> list[AgentDecision]:
        self._portfolios.get(portfolio_id)
        statement = (
            select(AgentDecision)
            .options(joinedload(AgentDecision.instrument))
            .where(AgentDecision.portfolio_id == portfolio_id)
            .order_by(AgentDecision.as_of.desc(), AgentDecision.id.desc())
        )
        return list(self._session.scalars(statement).unique().all())

    def get_decision(self, decision_id: int) -> AgentDecision:
        record = self._session.scalar(
            select(AgentDecision)
            .options(joinedload(AgentDecision.instrument))
            .where(AgentDecision.id == decision_id)
        )
        if record is None:
            raise UnknownDecisionError(decision_id)
        return record

    def _run_one(
        self,
        graph: Any,
        tools: AgentTools,
        portfolio_id: int,
        ticker: str,
        as_of: datetime.date,
        moment: datetime.datetime,
    ) -> AgentDecision | None:
        try:
            bars = self._market.get_history(ticker, as_of, limit=HISTORY_LIMIT)
        except UnknownTickerError:
            return None
        if not bars:
            return None
        started = time.perf_counter()
        result = graph.invoke(
            {
                "ticker": ticker,
                "as_of": as_of,
                "summary": technical_summary(bars),
                "decision": None,
                "order": None,
                "reports": {},
                "debate": [],
                "risk": None,
            }
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        decision = result["decision"]
        if decision is None:
            return None
        order = result["order"]
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            return None
        record = AgentDecision(
            portfolio_id=portfolio_id,
            instrument=instrument,
            instrument_id=instrument.id,
            as_of=as_of,
            action=AgentAction(decision.action),
            confidence=decision.confidence,
            target_weight=decision.target_weight,
            rationale=decision.rationale,
            llm_model=get_settings().llm_model,
            duration_ms=duration_ms,
            order_id=order.id if order is not None else None,
            reports=_dump_reports(result.get("reports")),
            debate=_dump_debate(result.get("debate")),
            risk=_dump_risk(result.get("risk")),
        )
        self._session.add(record)
        self._session.commit()
        self._portfolios.execute_pending_orders(portfolio_id, moment)
        return record


def _dump_reports(reports: dict[str, AnalystReport] | None) -> dict[str, object]:
    if not reports:
        return {}
    return {name: report.model_dump(mode="json") for name, report in reports.items()}


def _dump_debate(debate: list[DebateArgument] | None) -> list[object]:
    if not debate:
        return []
    return [item.model_dump(mode="json") for item in debate]


def _dump_risk(risk: RiskAssessment | None) -> dict[str, object] | None:
    if risk is None:
        return None
    return risk.model_dump(mode="json")


def _as_of_datetime(day: datetime.date) -> datetime.datetime:
    opened = session_open(day)
    if opened is not None:
        return opened
    return datetime.datetime.combine(day, datetime.time(12, 0), tzinfo=datetime.UTC)
