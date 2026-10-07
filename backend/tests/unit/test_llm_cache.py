from pydantic import BaseModel

from app.llm_cache import cache_key


class Answer(BaseModel):
    value: int


class Other(BaseModel):
    value: int


def test_same_inputs_share_a_key() -> None:
    first = cache_key("ollama", "qwen3:8b", 0, Answer, "sys", "user")
    second = cache_key("ollama", "qwen3:8b", 0.0, Answer, "sys", "user")
    assert first == second
    assert len(first) == 64


def test_prompt_or_model_change_invalidates_the_key() -> None:
    base = cache_key("ollama", "qwen3:8b", 0, Answer, "sys", "user")
    assert cache_key("ollama", "qwen3:8b", 0, Answer, "sys", "other") != base
    assert cache_key("ollama", "other", 0, Answer, "sys", "user") != base
    assert cache_key("ollama", "qwen3:8b", 0.2, Answer, "sys", "user") != base
    assert cache_key("ollama", "qwen3:8b", 0, Other, "sys", "user") != base
