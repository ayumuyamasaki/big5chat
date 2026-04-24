"""LLM provider abstractions."""

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse, LogprobEntry

__all__ = ["LLMProvider", "LLMResponse", "LogprobEntry"]


def get_provider(spec: str, **kwargs) -> LLMProvider:
    """Factory: create provider from 'provider:model' spec string.

    Example: 'openai:gpt-4.1' -> OpenAIProvider('gpt-4.1')
             'anthropic:claude-sonnet-4-5'
             'gemini:gemini-2.5-pro'
    """
    if ":" not in spec:
        raise ValueError(f"Provider spec must be 'provider:model', got: {spec}")
    provider_name, model = spec.split(":", 1)
    provider_name = provider_name.lower()

    if provider_name == "openai":
        from big5chat.dialogue.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(model=model, **kwargs)
    if provider_name == "anthropic":
        from big5chat.dialogue.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(model=model, **kwargs)
    if provider_name == "gemini":
        from big5chat.dialogue.providers.gemini_provider import GeminiProvider
        return GeminiProvider(model=model, **kwargs)
    raise ValueError(f"Unknown provider: {provider_name}")
