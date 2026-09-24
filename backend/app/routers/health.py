from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_session)],
) -> HealthService:
    return HealthService(settings, session)


@router.get("", response_model=HealthResponse)
def get_health(
    response: Response, service: Annotated[HealthService, Depends(get_health_service)]
) -> HealthResponse:
    """Returns 503 when a dependency fails, so Docker can detect an unhealthy service."""
    health = service.check()
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health
