"""LLM access behind a small protocol so agents stay provider-agnostic."""

from collections.abc import Sequence
from typing import Protocol, TypeVar, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

_ATTEMPTS = 2


class StructuredLLM(Protocol):
    def generate(self, schema: type[T], system: str, user: str) -> T: ...


class _Invoker(Protocol):
    def invoke(self, input: object) -> object: ...


class _Chat(Protocol):
    def with_structured_output(self, schema: type[BaseModel]) -> _Invoker: ...


class FakeLLM:
    """Returns prepared answers in order. Used by unit tests instead of Ollama."""

    def __init__(self, responses: Sequence[BaseModel]) -> None:
        self._responses = list(responses)
        self.prompts: list[tuple[type[BaseModel], str, str]] = []

    def generate(self, schema: type[T], system: str, user: str) -> T:
        self.prompts.append((schema, system, user))
        if not self._responses:
            raise IndexError("FakeLLM has no remaining responses")
        response = self._responses.pop(0)
        if not isinstance(response, schema):
            raise TypeError(f"expected {schema.__name__}, got {type(response).__name__}")
        return response


class OllamaLLM:
    """Local Ollama model with structured output. Thinking is disabled."""

    def __init__(self, chat: _Chat | None = None, model: str | None = None) -> None:
        if chat is not None:
            self._chat = chat
            return
        settings = get_settings()
        self._chat = cast(
            _Chat,
            ChatOllama(
                model=model or settings.llm_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
                reasoning=False,
            ),
        )

    def generate(self, schema: type[T], system: str, user: str) -> T:
        last_error: Exception | None = None
        for _ in range(_ATTEMPTS):
            try:
                raw = self._chat.with_structured_output(schema).invoke(
                    [SystemMessage(content=system), HumanMessage(content=user)]
                )
            except Exception as exc:
                last_error = exc
                continue
            if isinstance(raw, schema):
                return raw
            last_error = TypeError(f"expected {schema.__name__}, got {type(raw).__name__}")
        assert last_error is not None
        raise last_error
