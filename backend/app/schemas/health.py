from typing import Literal

from pydantic import BaseModel

ComponentStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    """`status` is `error` as soon as one dependency fails."""

    status: ComponentStatus
    environment: str
    database: ComponentStatus
