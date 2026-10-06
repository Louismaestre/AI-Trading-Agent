from pathlib import Path

from app.llm import StructuredLLM
from app.schemas.agents import AnalystReport
from app.schemas.fundamentals import FundamentalSnapshot

SYSTEM = (Path(__file__).resolve().parent / "prompts" / "fundamental_analyst.md").read_text(
    encoding="utf-8"
)

_NO_FILINGS = AnalystReport(
    stance="NEUTRAL",
    confidence=0.2,
    rationale="No public filings at as_of.",
)


def report(llm: StructuredLLM, snapshot: FundamentalSnapshot) -> AnalystReport:
    """Judge the name from filings already public at `snapshot.as_of`."""
    if not snapshot.statements:
        return _NO_FILINGS
    user = f"""
    Fundamentals known at as_of:
    {snapshot.model_dump_json()}
    """
    return llm.generate(AnalystReport, SYSTEM, user)
