"""OpenAI (GPT-4.1 family) provider with logprobs + seed support."""

from __future__ import annotations

import os
from typing import Any

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse, LogprobEntry


class OpenAIProvider(LLMProvider):
    """OpenAI Chat Completions wrapper.

    Fully supports seed + logprobs, which makes it the primary choice per
    ConstructionPlan.md §E. Uses the async client.
    """

    provider_name = "openai"
    supports_logprobs = True
    supports_seed = True

    def __init__(self, model: str = "gpt-4.1", api_key: str | None = None):
        super().__init__(model)
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

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
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if seed is not None:
            kwargs["seed"] = seed
        if logprobs:
            kwargs["logprobs"] = True
            if top_logprobs > 0:
                kwargs["top_logprobs"] = min(top_logprobs, 20)
        if stop:
            kwargs["stop"] = stop

        resp = await self.client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        lp_entries: list[LogprobEntry] = []
        if logprobs and choice.logprobs and choice.logprobs.content:
            for tok in choice.logprobs.content:
                top_lps = {t.token: t.logprob for t in (tok.top_logprobs or [])}
                lp_entries.append(
                    LogprobEntry(token=tok.token, logprob=tok.logprob, top_logprobs=top_lps)
                )

        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content=choice.message.content or "",
            model_id=resp.model,
            provider=self.provider_name,
            seed=seed,
            system_fingerprint=getattr(resp, "system_fingerprint", None),
            temperature=temperature,
            top_p=top_p,
            stop_reason=choice.finish_reason,
            input_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
            output_tokens=getattr(usage, "completion_tokens", None) if usage else None,
            logprobs=lp_entries,
            raw={"id": resp.id, "created": resp.created},
        )
