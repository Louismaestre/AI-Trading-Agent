from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_engine, get_session
from app.models import EquityPoint, Replay, ReplayStatus
from app.routers.agents import decision_response
from app.schemas.agents import AgentDecisionResponse
from app.schemas.live import EquityPointResponse
from app.schemas.replay import CreateReplayRequest, ReplayMetricsResponse, ReplayResponse
from app.services.metrics import ReplayMetrics
from app.services.replay_service import (
    EmptyReplayRangeError,
    ReplayService,
    ReplayStartsTooEarlyError,
    UnknownReplayError,
)

router = APIRouter(prefix="/replays", tags=["replays"])
_jobs = ThreadPoolExecutor(max_workers=1, thread_name_prefix="replay")


def get_replay_service(session: Annotated[Session, Depends(get_session)]) -> ReplayService:
    return ReplayService(session)


def run_replay_job(replay_id: int) -> None:
    """Fresh session: the request session is closed before a background job runs."""
    with Session(get_engine()) as session:
        ReplayService(session).run(replay_id)


@router.post("", response_model=ReplayResponse, status_code=status.HTTP_201_CREATED)
def start_replay(
    request: CreateReplayRequest,
    service: Annotated[ReplayService, Depends(get_replay_service)],
) -> ReplayResponse:
    try:
        replay = service.start(
            request.name,
            request.initial_capital,
            request.start,
            request.end,
            decision_frequency=request.decision_frequency,
        )
    except (ReplayStartsTooEarlyError, EmptyReplayRangeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    if get_settings().app_env == "test":
        replay = service.run(replay.id)
    else:
        _jobs.submit(run_replay_job, replay.id)
    return _replay_response(service, replay)


@router.get("/{replay_id}", response_model=ReplayResponse)
def read_replay(
    replay_id: int,
    service: Annotated[ReplayService, Depends(get_replay_service)],
) -> ReplayResponse:
    try:
        replay = service.get(replay_id)
    except UnknownReplayError:
        raise _unknown_replay(replay_id) from None
    return _replay_response(service, replay)


@router.get("/{replay_id}/equity", response_model=list[EquityPointResponse])
def list_equity(
    replay_id: int,
    service: Annotated[ReplayService, Depends(get_replay_service)],
) -> list[EquityPointResponse]:
    try:
        return [_equity_response(point) for point in service.list_equity(replay_id)]
    except UnknownReplayError:
        raise _unknown_replay(replay_id) from None


@router.get("/{replay_id}/decisions", response_model=list[AgentDecisionResponse])
def list_decisions(
    replay_id: int,
    service: Annotated[ReplayService, Depends(get_replay_service)],
) -> list[AgentDecisionResponse]:
    try:
        return [decision_response(record) for record in service.list_decisions(replay_id)]
    except UnknownReplayError:
        raise _unknown_replay(replay_id) from None


@router.get("/{replay_id}/metrics", response_model=ReplayMetricsResponse)
def read_metrics(
    replay_id: int,
    service: Annotated[ReplayService, Depends(get_replay_service)],
) -> ReplayMetricsResponse:
    try:
        return _metrics_response(service.metrics(replay_id))
    except UnknownReplayError:
        raise _unknown_replay(replay_id) from None


def _replay_response(service: ReplayService, replay: Replay) -> ReplayResponse:
    scored = None
    if replay.status is ReplayStatus.DONE:
        scored = _metrics_response(service.metrics(replay.id))
    return ReplayResponse(
        id=replay.id,
        portfolio_id=replay.portfolio_id,
        kind=replay.kind,
        status=replay.status,
        start_date=replay.start_date,
        end_date=replay.end_date,
        days_done=replay.days_done,
        days_total=replay.days_total,
        current_date=replay.current_date,
        decision_frequency=replay.decision_frequency,
        error_message=replay.error_message,
        benchmark_replay_id=replay.benchmark_replay_id,
        sma_replay_id=replay.sma_replay_id,
        random_replay_id=replay.random_replay_id,
        metrics=scored,
    )


def _metrics_response(scored: ReplayMetrics) -> ReplayMetricsResponse:
    return ReplayMetricsResponse(
        total_return=scored.total_return,
        max_drawdown=scored.max_drawdown,
        order_count=scored.order_count,
        fees_paid=scored.fees_paid,
        hit_rate=scored.hit_rate,
    )


def _equity_response(point: EquityPoint) -> EquityPointResponse:
    return EquityPointResponse(
        id=point.id,
        recorded_at=point.recorded_at,
        total_value=point.total_value,
        cash=point.cash,
    )


def _unknown_replay(replay_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown replay: {replay_id}"
    )
