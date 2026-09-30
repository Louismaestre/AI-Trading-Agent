import datetime
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import EquityPoint, LiveSession, LiveSessionStatus
from app.routers.agents import decision_response
from app.scheduler import next_trigger
from app.schemas.agents import AgentDecisionResponse
from app.schemas.live import CreateLiveSessionRequest, EquityPointResponse, LiveSessionResponse
from app.services.live_service import (
    InvalidLiveSessionStateError,
    LiveService,
    UnknownLiveSessionError,
)
from app.services.portfolio_service import PortfolioView

router = APIRouter(prefix="/live-sessions", tags=["live"])


def get_live_service(session: Annotated[Session, Depends(get_session)]) -> LiveService:
    return LiveService(session)


@router.post("", response_model=LiveSessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    request: CreateLiveSessionRequest,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSessionResponse:
    now = datetime.datetime.now(datetime.UTC)
    live = service.start(request.name, request.initial_capital, request.interval_minutes, now=now)
    return _session_response(service, live, now)


@router.get("/{session_id}", response_model=LiveSessionResponse)
def read_session(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
    now: AwareDatetime | None = None,
) -> LiveSessionResponse:
    moment = now or datetime.datetime.now(datetime.UTC)
    try:
        live = service.get(session_id)
    except UnknownLiveSessionError:
        raise _unknown_session(session_id) from None
    return _session_response(service, live, moment)


@router.post("/{session_id}/pause", response_model=LiveSessionResponse)
def pause_session(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSessionResponse:
    return _mutate(session_id, service, service.pause)


@router.post("/{session_id}/resume", response_model=LiveSessionResponse)
def resume_session(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSessionResponse:
    return _mutate(session_id, service, service.resume)


@router.post("/{session_id}/stop", response_model=LiveSessionResponse)
def stop_session(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> LiveSessionResponse:
    return _mutate(session_id, service, service.stop)


@router.get("/{session_id}/equity", response_model=list[EquityPointResponse])
def list_equity(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> list[EquityPointResponse]:
    try:
        return [_equity_response(point) for point in service.list_equity(session_id)]
    except UnknownLiveSessionError:
        raise _unknown_session(session_id) from None


@router.get("/{session_id}/decisions", response_model=list[AgentDecisionResponse])
def list_decisions(
    session_id: int,
    service: Annotated[LiveService, Depends(get_live_service)],
) -> list[AgentDecisionResponse]:
    try:
        return [decision_response(record) for record in service.list_decisions(session_id)]
    except UnknownLiveSessionError:
        raise _unknown_session(session_id) from None


def _mutate(
    session_id: int,
    service: LiveService,
    action: Callable[[int], LiveSession],
) -> LiveSessionResponse:
    now = datetime.datetime.now(datetime.UTC)
    try:
        live = action(session_id)
    except UnknownLiveSessionError:
        raise _unknown_session(session_id) from None
    except InvalidLiveSessionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return _session_response(service, live, now)


def _session_response(
    service: LiveService, live: LiveSession, now: datetime.datetime
) -> LiveSessionResponse:
    view: PortfolioView = service.portfolio_snapshot(live.portfolio_id, now)
    next_at = (
        next_trigger(now, live.interval_minutes)
        if live.status is LiveSessionStatus.RUNNING
        else None
    )
    return LiveSessionResponse(
        id=live.id,
        portfolio_id=live.portfolio_id,
        kind=live.kind,
        status=live.status,
        interval_minutes=live.interval_minutes,
        started_at=live.started_at,
        last_slot=live.last_slot,
        next_cycle_at=next_at,
        total_value=view.total_value,
        cash=view.portfolio.cash,
        benchmark_session_id=live.benchmark_session_id,
    )


def _equity_response(point: EquityPoint) -> EquityPointResponse:
    return EquityPointResponse(
        id=point.id,
        recorded_at=point.recorded_at,
        total_value=point.total_value,
        cash=point.cash,
    )


def _unknown_session(session_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown live session: {session_id}"
    )
