"""LLM プロバイダ抽象化レイヤ。"""

from big5_persona_chat.providers.base import LLMProvider, LLMResponse, LogprobEntry

__all__ = ["LLMProvider", "LLMResponse", "LogprobEntry", "get_provider"]


def get_provider(spec: str, **kwargs) -> LLMProvider:
    """'provider:model' 形式の文字列からプロバイダを生成するファクトリ。

    例:
        'openai:gpt-4.1'           -> OpenAIProvider('gpt-4.1')
        'anthropic:claude-sonnet-4-5'
        'gemini:gemini-2.5-pro'
    """
    if ":" not in spec:
        raise ValueError(f"プロバイダ指定は 'provider:model' 形式である必要があります: {spec}")
    provider_name, model = spec.split(":", 1)
    provider_name = provider_name.lower()

    if provider_name == "openai":
        from big5_persona_chat.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(model=model, **kwargs)
    if provider_name == "anthropic":
        from big5_persona_chat.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(model=model, **kwargs)
    if provider_name == "gemini":
        from big5_persona_chat.providers.gemini_provider import GeminiProvider
        return GeminiProvider(model=model, **kwargs)
    raise ValueError(f"未知のプロバイダ: {provider_name}")
