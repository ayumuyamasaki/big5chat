"""Shared pytest fixtures and mock provider."""

from __future__ import annotations

import pytest

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse, LogprobEntry
from big5chat.persona.spec import Big5Values, PersonaSpec


class MockProvider(LLMProvider):
    """Stub provider returning deterministic fixed responses.

    Configure by setting self.next_response (a single string) or self.response_queue
    (a list of strings used in FIFO order).
    """

    provider_name = "mock"
    supports_logprobs = True
    supports_seed = True

    def __init__(self, model: str = "mock-model"):
        super().__init__(model)
        self.next_response = "3"
        self.response_queue: list[str] = []
        self.calls: list[dict] = []

    async def complete(
        self,
        messages,
        *,
        temperature=0.7,
        top_p=0.95,
        seed=None,
        max_tokens=400,
        logprobs=False,
        top_logprobs=0,
        stop=None,
    ) -> LLMResponse:
        content = (
            self.response_queue.pop(0)
            if self.response_queue
            else self.next_response
        )
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "seed": seed,
                "max_tokens": max_tokens,
            }
        )
        lp = []
        if logprobs and content:
            first_token = content[:1]
            lp.append(
                LogprobEntry(
                    token=first_token,
                    logprob=-0.1,
                    top_logprobs={"A": -0.5, "B": -1.0, "C": -2.0, "D": -3.0},
                )
            )
        return LLMResponse(
            content=content,
            model_id=self.model,
            provider=self.provider_name,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            input_tokens=10,
            output_tokens=len(content),
            logprobs=lp,
            raw={},
        )


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def sample_spec_ja() -> PersonaSpec:
    return PersonaSpec(
        profile_id="test_highE",
        big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0,
        item_postamble_id=0,
        prompt_variant="A",
        language="ja",
    )


@pytest.fixture
def sample_spec_en() -> PersonaSpec:
    return PersonaSpec(
        profile_id="test_highE_en",
        big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0,
        item_postamble_id=0,
        prompt_variant="A",
        language="en",
    )
