from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.routers.replays import _jobs, _replay_response, run_replay_job
from app.schemas.experiments import ExperimentResponse
from app.schemas.replay import ExperimentRunResponse
from app.services.experiment_service import MAX_REPEATS, ExperimentService, UnknownExperimentError
from app.services.replay_service import (
    EmptyReplayRangeError,
    ReplayService,
    ReplayStartsTooEarlyError,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


def get_experiment_service(session: Annotated[Session, Depends(get_session)]) -> ExperimentService:
    return ExperimentService(session)


@router.get("", response_model=list[ExperimentResponse])
def list_experiments(
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
) -> list[ExperimentResponse]:
    return [ExperimentResponse.model_validate(item.model_dump()) for item in service.list_all()]


@router.post("/{experiment_id}/replays", response_model=ExperimentRunResponse, status_code=201)
def start_experiment(
    experiment_id: str,
    service: Annotated[ExperimentService, Depends(get_experiment_service)],
    session: Annotated[Session, Depends(get_session)],
    repeats: Annotated[int, Query(ge=1, le=MAX_REPEATS)] = 1,
) -> ExperimentRunResponse:
    try:
        started = service.start(experiment_id, repeats=repeats)
    except UnknownExperimentError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown experiment: {experiment_id}"
        ) from None
    except (ReplayStartsTooEarlyError, EmptyReplayRangeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    if get_settings().app_env == "test":
        started = [service.run(row.id) for row in started]
    else:
        for row in started:
            _jobs.submit(run_replay_job, row.id)
    replays = ReplayService(session)
    return ExperimentRunResponse(
        batch_id=started[0].batch_id or "",
        repeats=[_replay_response(replays, row) for row in started],
    )
