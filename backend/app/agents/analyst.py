import datetime
import json
from pathlib import Path

from app.agents.debate import format_transcript
from app.llm import StructuredLLM
from app.schemas.agents import (
    AnalystDecision,
    AnalystReport,
    DebateArgument,
    PriorYearContext,
    TechnicalSummary,
)
from app.schemas.portfolio import PositionResponse

SYSTEM = (Path(__file__).resolve().parent / "prompts" / "analyst.md").read_text(encoding="utf-8")


def decide(
    llm: StructuredLLM,
    summary: TechnicalSummary,
    position: PositionResponse | None,
    as_of: datetime.date,
    reports: dict[str, AnalystReport] | None = None,
    prior_year: PriorYearContext | None = None,
    debate: list[DebateArgument] | None = None,
) -> AnalystDecision:
    """Decide whether to buy, sell or hold a position."""
    position_json = position.model_dump_json() if position is not None else "none"
    reports_json = (
        json.dumps({name: report.model_dump(mode="json") for name, report in reports.items()})
        if reports
        else "none"
    )
    prior_json = prior_year.model_dump_json() if prior_year is not None else "none"
    system = SYSTEM
    user = f"""
    Technical summary:
    {summary.model_dump_json()}

    Position:
    {position_json}

    As of:
    {as_of}

    Prior completed year vs CAC 40 (already over; not the current year):
    {prior_json}

    Reports:
    {reports_json}

    Debate transcript:
    {format_transcript(debate or [])}
    """
    return llm.generate(AnalystDecision, system, user)
