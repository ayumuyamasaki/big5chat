"""Anthropic (Claude Sonnet 4.5 family) provider.

No logprobs; no seed. Use temperature=0 + repetition averaging for reproducibility.
"""

from __future__ import annotations

import os

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse


def _split_system(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """Claude API expects system as a top-level param, not in messages."""
    system_parts: list[str] = []
    other: list[dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            other.append(m)
    return "\n\n".join(system_parts), other


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API wrapper."""

    provider_name = "anthropic"
    supports_logprobs = False
    supports_seed = False

    def __init__(self, model: str = "claude-sonnet-4-5", api_key: str | None = None):
        super().__init__(model)
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        top_p: float = 0.95,
        seed: int | None = None,  # ignored - Claude has no seed param
        max_tokens: int = 400,
        logprobs: bool = False,  # ignored
        top_logprobs: int = 0,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        system, chat_msgs = _split_system(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": chat_msgs,
        }
        if system:
            kwargs["system"] = system
        if stop:
            kwargs["stop_sequences"] = stop

        resp = await self.client.messages.create(**kwargs)

        content = ""
        if resp.content:
            # Concatenate text blocks only (ignore tool_use blocks)
            content = "".join(
                b.text for b in resp.content if getattr(b, "type", "") == "text"
            )

        return LLMResponse(
            content=content,
            model_id=resp.model,
            provider=self.provider_name,
            seed=None,
            system_fingerprint=None,
            temperature=temperature,
            top_p=top_p,
            stop_reason=resp.stop_reason,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            logprobs=[],
            raw={"id": resp.id},
        )
