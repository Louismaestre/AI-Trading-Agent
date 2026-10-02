import datetime
from operator import add
from typing import Annotated, TypedDict

from app.models import Order
from app.schemas.agents import AnalystDecision, AnalystReport, DebateArgument, TechnicalSummary


def merge_reports(
    left: dict[str, AnalystReport],
    right: dict[str, AnalystReport],
) -> dict[str, AnalystReport]:
    return {**left, **right}


class AgentState(TypedDict):
    ticker: str
    as_of: datetime.date
    summary: TechnicalSummary
    decision: AnalystDecision | None
    order: Order | None
    reports: Annotated[dict[str, AnalystReport], merge_reports]
    debate: Annotated[list[DebateArgument], add]
