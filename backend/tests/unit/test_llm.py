import urllib.error
import urllib.request

import pytest
from pydantic import BaseModel

from app.config import get_settings
from app.llm import FakeLLM, OllamaLLM


class Answer(BaseModel):
    value: int


class _FailThenSucceed:
    def __init__(self) -> None:
        self.calls = 0

    def with_structured_output(self, schema: type[BaseModel]) -> "_FailThenSucceed":
        self.schema = schema
        return self

    def invoke(self, _input: object) -> object:
        self.calls += 1
        if self.calls == 1:
            raise ValueError("invalid output")
        return Answer(value=7)


class _AlwaysInvalid:
    def with_structured_output(self, _schema: type[BaseModel]) -> "_AlwaysInvalid":
        return self

    def invoke(self, _input: object) -> object:
        return {"value": 1}


def test_fake_llm_returns_responses_in_order() -> None:
    llm = FakeLLM([Answer(value=1), Answer(value=2)])

    assert llm.generate(Answer, "system", "first").value == 1
    assert llm.generate(Answer, "system", "second").value == 2
    assert [user for _schema, _system, user in llm.prompts] == ["first", "second"]


def test_fake_llm_runs_out_of_responses() -> None:
    llm = FakeLLM([])

    with pytest.raises(IndexError, match="no remaining responses"):
        llm.generate(Answer, "system", "user")


def test_ollama_retries_once_after_invalid_output() -> None:
    chat = _FailThenSucceed()
    llm = OllamaLLM(chat=chat)

    assert llm.generate(Answer, "system", "user").value == 7
    assert chat.calls == 2


def test_ollama_gives_up_after_two_invalid_outputs() -> None:
    llm = OllamaLLM(chat=_AlwaysInvalid())

    with pytest.raises(TypeError, match="expected Answer"):
        llm.generate(Answer, "system", "user")


def _ollama_is_up() -> bool:
    url = get_settings().ollama_base_url.rstrip("/") + "/api/tags"
    try:
        urllib.request.urlopen(url, timeout=2)
    except (urllib.error.URLError, TimeoutError):
        return False
    return True


@pytest.mark.llm
def test_ollama_returns_a_valid_structured_object() -> None:
    if not _ollama_is_up():
        pytest.skip("Ollama is not running")

    result = OllamaLLM().generate(
        Answer,
        "You only fill the structured fields.",
        "Reply with value 3.",
    )
    assert isinstance(result, Answer)
