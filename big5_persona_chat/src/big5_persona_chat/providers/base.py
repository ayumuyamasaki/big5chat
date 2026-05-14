"""LLMProvider abstract base class and LLMResponse data model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LogprobEntry(BaseModel):
    """単一トークンの log 確率と上位候補。"""

    token: str
    logprob: float
    top_logprobs: dict[str, float] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """プロバイダ横断の統一レスポンススキーマ。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: str
    model_id: str
    provider: str
    seed: int | None = None
    system_fingerprint: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    logprobs: list[LogprobEntry] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class LLMProvider(ABC):
    """LLM プロバイダの抽象インタフェース。"""

    provider_name: str = ""

    def __init__(self, model: str):
        self.model = model

    @property
    @abstractmethod
    def supports_logprobs(self) -> bool: ...

    @property
    @abstractmethod
    def supports_seed(self) -> bool: ...

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        top_p: float = 0.95,
        seed: int | None = None,
        max_tokens: int = 400,
        logprobs: bool = False,
        top_logprobs: int = 0,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """補完リクエストを送る。messages は OpenAI 形式。"""
        ...
