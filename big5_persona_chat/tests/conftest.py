"""共有 pytest フィクスチャとモックプロバイダ。"""

from __future__ import annotations

import importlib

import pytest

from big5_persona_chat.persona import Big5, Persona
from big5_persona_chat.providers.base import LLMProvider, LLMResponse

# big5_persona_chat.__init__ が `from big5_persona_chat.chat import chat, ...` を
# 実行しているため、パッケージの `chat` 属性は submodule ではなく chat() 関数に
# 上書きされている。`import big5_persona_chat.chat as m` 相当の属性経由の解決も
# 同じ理由で関数を返してしまうため、sys.modules 経由で確実に submodule を取得する。
chat_module = importlib.import_module("big5_persona_chat.chat")


class MockProvider(LLMProvider):
    """決定的な固定応答を返すスタブプロバイダ。

    self.next_response (単一文字列) または self.response_queue
    (FIFO で消費される文字列リスト) で応答内容を設定する。
    呼び出しの度に self.calls に messages 等を記録するため、
    ChatSession の再注入ロジックなどを検証できる。
    """

    provider_name = "mock"
    supports_logprobs = False
    supports_seed = True

    def __init__(self, model: str = "mock-model"):
        super().__init__(model)
        self.next_response = "mock response"
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
        content = self.response_queue.pop(0) if self.response_queue else self.next_response
        self.calls.append(
            {
                "messages": messages,
                "temperature": temperature,
                "seed": seed,
                "max_tokens": max_tokens,
            }
        )
        return LLMResponse(
            content=content,
            model_id=self.model,
            provider=self.provider_name,
            seed=seed,
            temperature=temperature,
            top_p=top_p,
            stop_reason="stop",
            input_tokens=10,
            output_tokens=len(content),
            raw={},
        )


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def mock_get_provider(monkeypatch, mock_provider: MockProvider):
    """big5_persona_chat.chat.get_provider を MockProvider を返す差し替え関数にする。

    ChatSession / chat() はモデル文字列に関わらず同じ MockProvider インスタンスを
    使うため、mock_provider.calls から実際に送られた messages を検証できる。
    """

    def _fake_get_provider(spec: str, **kwargs):
        return mock_provider

    # 文字列パス指定だと big5_persona_chat.__init__ が再エクスポートしている
    # `chat`(関数)と submodule `chat` の名前衝突により誤解決するため、
    # submodule オブジェクトを直接 import してから setattr する。
    monkeypatch.setattr(chat_module, "get_provider", _fake_get_provider)
    return mock_provider


@pytest.fixture
def extravert_leader() -> Persona:
    """pptx記載の8プリセットの1つ。EXTRAVERT_LEADER (E突出, A=+1)。"""
    return Persona(
        big5=Big5(O=2, C=2, E=3, A=1, N=-2),
        biography_id=2,
        name="EXTRAVERT_LEADER",
    )


@pytest.fixture
def introvert_thinker() -> Persona:
    """pptx記載の8プリセットの1つ。INTROVERT_THINKER (E=-3)。"""
    return Persona(
        big5=Big5(O=3, C=2, E=-3, A=1, N=0),
        biography_id=3,
        name="INTROVERT_THINKER",
    )
