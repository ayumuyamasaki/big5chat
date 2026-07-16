"""get_provider() ファクトリの契約の検証。

各プロバイダの __init__ は SDK クライアントを生成するだけでネットワーク接続は
行わないため、APIキー無しでもオフラインで検証できる。
"""

from __future__ import annotations

import pytest

from big5_persona_chat.providers import get_provider
from big5_persona_chat.providers.anthropic_provider import AnthropicProvider
from big5_persona_chat.providers.gemini_provider import GeminiProvider
from big5_persona_chat.providers.openai_provider import OpenAIProvider


def test_get_provider_openai():
    provider = get_provider("openai:gpt-4.1")
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4.1"
    assert provider.supports_seed is True
    assert provider.supports_logprobs is True


def test_get_provider_anthropic():
    provider = get_provider("anthropic:claude-sonnet-4-5")
    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-sonnet-4-5"
    assert provider.supports_seed is False


def test_get_provider_gemini():
    provider = get_provider("gemini:gemini-2.5-pro")
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-2.5-pro"
    assert provider.supports_seed is False


def test_get_provider_rejects_missing_colon():
    with pytest.raises(ValueError):
        get_provider("gpt-4.1")


def test_get_provider_rejects_unknown_provider():
    with pytest.raises(ValueError):
        get_provider("unknown_provider:some-model")
