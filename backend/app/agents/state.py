import datetime
from typing import TypedDict

from app.models import Order
from app.schemas.agents import AnalystDecision, TechnicalSummary


class AgentState(TypedDict):
    ticker: str
    as_of: datetime.date
    summary: TechnicalSummary
    decision: AnalystDecision | None
    order: Order | None
