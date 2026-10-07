"""Persist structured LLM answers so identical replay calls are not paid twice."""

import hashlib
import json
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm import StructuredLLM
from app.models import LlmCache

T = TypeVar("T", bound=BaseModel)


def cache_key(
    provider: str,
    model: str,
    temperature: float,
    schema: type[BaseModel],
    system: str,
    user: str,
) -> str:
    """SHA-256 of everything that must stay equal for a replay to reuse an answer."""
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "temperature": float(temperature),
            "schema": schema.model_json_schema(),
            "system": system,
            "user": user,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CachedLLM:
    """Same `generate` as the inner model. Hits skip the inner call."""

    def __init__(
        self,
        inner: StructuredLLM,
        session: Session,
        *,
        provider: str,
        model: str,
        temperature: float,
        enabled: bool = True,
    ) -> None:
        self._inner = inner
        self._session = session
        self._provider = provider
        self._model = model
        self._temperature = temperature
        self._enabled = enabled

    def generate(self, schema: type[T], system: str, user: str) -> T:
        if not self._enabled:
            return self._inner.generate(schema, system, user)
        key = cache_key(self._provider, self._model, self._temperature, schema, system, user)
        hit = self._read(key, schema)
        if hit is not None:
            return hit
        result = self._inner.generate(schema, system, user)
        self._write(key, schema, result)
        return result

    def _read(self, key: str, schema: type[T]) -> T | None:
        row = self._session.scalar(select(LlmCache).where(LlmCache.cache_key == key))
        if row is None:
            return None
        try:
            return schema.model_validate(row.response)
        except Exception:
            return None

    def _write(self, key: str, schema: type[BaseModel], result: BaseModel) -> None:
        self._session.add(
            LlmCache(
                cache_key=key,
                model=self._model,
                schema_name=schema.__name__,
                response=result.model_dump(mode="json"),
            )
        )
        self._session.flush()
