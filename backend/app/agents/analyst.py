import datetime
from pathlib import Path

from app.llm import StructuredLLM
from app.schemas.agents import AnalystDecision, TechnicalSummary
from app.schemas.portfolio import PositionResponse

SYSTEM = (Path(__file__).resolve().parent / "prompts" / "analyst.md").read_text(encoding="utf-8")


def decide(
    llm: StructuredLLM,
    summary: TechnicalSummary,
    position: PositionResponse | None,
    as_of: datetime.date,
) -> AnalystDecision:
    """Decide whether to buy, sell or hold a position."""
    position_json = position.model_dump_json() if position is not None else "none"

    system = SYSTEM
    user = f"""
    Technical summary:
    {summary.model_dump_json()}

    Position:
    {position_json}

    As of:
    {as_of}
    """
    return llm.generate(AnalystDecision, system, user)
