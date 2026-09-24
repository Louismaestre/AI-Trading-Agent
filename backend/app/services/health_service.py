import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings
from app.schemas.health import ComponentStatus, HealthResponse

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, settings: Settings, session: Session) -> None:
        self._settings = settings
        self._session = session

    def check(self) -> HealthResponse:
        database = self._ping_database()
        return HealthResponse(
            status=database, environment=self._settings.app_env, database=database
        )

    def _ping_database(self) -> ComponentStatus:
        try:
            self._session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.exception("Database health check failed")
            return "error"
        return "ok"
