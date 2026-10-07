from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm import FakeLLM
from app.llm_cache import CachedLLM
from app.models import LlmCache


class Answer(BaseModel):
    value: int


def _cached(session: Session, inner: FakeLLM, *, model: str = "qwen3:8b") -> CachedLLM:
    return CachedLLM(inner, session, provider="fake", model=model, temperature=0)


def test_identical_calls_hit_the_cache(db_session: Session) -> None:
    inner = FakeLLM([Answer(value=7)])
    llm = _cached(db_session, inner)

    assert llm.generate(Answer, "sys", "user").value == 7
    assert llm.generate(Answer, "sys", "user").value == 7
    assert len(inner.prompts) == 1
    assert db_session.scalar(select(func.count(LlmCache.id))) == 1


def test_a_different_prompt_or_model_misses(db_session: Session) -> None:
    inner = FakeLLM([Answer(value=1), Answer(value=2), Answer(value=3)])
    llm = _cached(db_session, inner)

    assert llm.generate(Answer, "sys", "first").value == 1
    assert llm.generate(Answer, "sys", "second").value == 2
    other = _cached(db_session, inner, model="other")
    assert other.generate(Answer, "sys", "first").value == 3
    assert len(inner.prompts) == 3


def test_disabled_cache_always_calls_the_inner_model(db_session: Session) -> None:
    inner = FakeLLM([Answer(value=1), Answer(value=2)])
    llm = CachedLLM(
        inner, db_session, provider="fake", model="qwen3:8b", temperature=0, enabled=False
    )

    assert llm.generate(Answer, "sys", "user").value == 1
    assert llm.generate(Answer, "sys", "user").value == 2
    assert db_session.scalar(select(func.count(LlmCache.id))) == 0
