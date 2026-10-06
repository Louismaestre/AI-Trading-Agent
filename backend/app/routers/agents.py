import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import AgentDecision
from app.schemas.agents import (
    AgentDecisionDetailResponse,
    AgentDecisionResponse,
    AnalystReport,
    DebateArgument,
    RiskAssessment,
)
from app.services.agent_service import AgentService, UnknownDecisionError
from app.services.portfolio_service import UnknownPortfolioError

router = APIRouter(prefix="/portfolios", tags=["agents"])
decisions_router = APIRouter(prefix="/decisions", tags=["agents"])


def get_agent_service(session: Annotated[Session, Depends(get_session)]) -> AgentService:
    return AgentService(session)


@router.post(
    "/{portfolio_id}/run-agents",
    response_model=list[AgentDecisionResponse],
    status_code=status.HTTP_201_CREATED,
)
def run_agents(
    portfolio_id: int,
    service: Annotated[AgentService, Depends(get_agent_service)],
    as_of: datetime.date | None = None,
) -> list[AgentDecisionResponse]:
    try:
        records = service.run_agents(portfolio_id, as_of or datetime.date.today())
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None
    return [decision_response(record) for record in records]


@router.get("/{portfolio_id}/decisions", response_model=list[AgentDecisionResponse])
def list_decisions(
    portfolio_id: int,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> list[AgentDecisionResponse]:
    try:
        return [decision_response(record) for record in service.list_decisions(portfolio_id)]
    except UnknownPortfolioError:
        raise _unknown_portfolio(portfolio_id) from None


@decisions_router.get("/{decision_id}", response_model=AgentDecisionDetailResponse)
def get_decision(
    decision_id: int,
    service: Annotated[AgentService, Depends(get_agent_service)],
) -> AgentDecisionDetailResponse:
    try:
        return decision_detail(service.get_decision(decision_id))
    except UnknownDecisionError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown decision: {decision_id}"
        ) from None


def decision_response(record: AgentDecision) -> AgentDecisionResponse:
    return AgentDecisionResponse(
        id=record.id,
        ticker=record.instrument.ticker,
        as_of=record.as_of,
        created_at=record.created_at,
        action=record.action.value,
        confidence=record.confidence,
        target_weight=record.target_weight,
        rationale=record.rationale,
        llm_model=record.llm_model,
        duration_ms=record.duration_ms,
        order_id=record.order_id,
    )


def decision_detail(record: AgentDecision) -> AgentDecisionDetailResponse:
    base = decision_response(record)
    return AgentDecisionDetailResponse(
        **base.model_dump(),
        reports=_load_reports(record.reports),
        debate=_load_debate(record.debate),
        risk=_load_risk(record.risk),
    )


def _load_reports(raw: dict[str, object] | None) -> dict[str, AnalystReport]:
    if not raw:
        return {}
    return {name: AnalystReport.model_validate(item) for name, item in raw.items()}


def _load_debate(raw: list[object] | None) -> list[DebateArgument]:
    if not raw:
        return []
    return [DebateArgument.model_validate(item) for item in raw]


def _load_risk(raw: dict[str, object] | None) -> RiskAssessment | None:
    if raw is None:
        return None
    return RiskAssessment.model_validate(raw)


def _unknown_portfolio(portfolio_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown portfolio: {portfolio_id}"
    )
