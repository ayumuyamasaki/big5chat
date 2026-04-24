"""Google Gemini (2.5 Pro / Flash) provider.

Supports logprobs and (partial) seed via Vertex AI. Uses google-genai SDK.
"""

from __future__ import annotations

import asyncio
import os

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse


def _to_gemini_contents(messages: list[dict[str, str]]) -> tuple[str, list[dict]]:
    """Gemini takes a system_instruction separately, then a contents list
    of role=user|model messages."""
    system_parts: list[str] = []
    contents: list[dict] = []
    for m in messages:
        role = m["role"]
        text = m["content"]
        if role == "system":
            system_parts.append(text)
        elif role == "user":
            contents.append({"role": "user", "parts": [{"text": text}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
    return "\n\n".join(system_parts), contents


class GeminiProvider(LLMProvider):
    """Google Gemini wrapper using google-genai.

    NOTE: As of 2025, google-genai client is synchronous; we offload to a thread.
    """

    provider_name = "gemini"
    supports_logprobs = True
    supports_seed = False  # True only under Vertex AI; skip for safety

    def __init__(self, model: str = "gemini-2.5-pro", api_key: str | None = None):
        super().__init__(model)
        from google import genai
        self.client = genai.Client(api_key=api_key or os.environ.get("GOOGLE_API_KEY"))

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
        system, contents = _to_gemini_contents(messages)

        from google.genai import types as gtypes

        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_tokens,
            system_instruction=system or None,
            stop_sequences=stop,
            response_logprobs=logprobs or None,
            logprobs=top_logprobs if logprobs and top_logprobs > 0 else None,
        )

        # google-genai is sync - offload to thread.
        def _call():
            return self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

        resp = await asyncio.to_thread(_call)

        content = resp.text or ""
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            content=content,
            model_id=self.model,
            provider=self.provider_name,
            seed=None,
            system_fingerprint=None,
            temperature=temperature,
            top_p=top_p,
            stop_reason=None,
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
            logprobs=[],  # parsing gemini logprobs left for future
            raw={"model": self.model},
        )
