import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import AgentDecision
from app.schemas.agents import AgentDecisionResponse
from app.services.agent_service import AgentService
from app.services.portfolio_service import UnknownPortfolioError

router = APIRouter(prefix="/portfolios", tags=["agents"])


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


def _unknown_portfolio(portfolio_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown portfolio: {portfolio_id}"
    )
