"""実際の LLM API を呼び出す統合テスト。

pptx (Big5チャットボットの使い方と設計.pptx) スライド3・4のコード例をほぼ
そのまま実行し、big5_persona_chat が実際に動作することを確認する。

課金・ネットワークが必要なため既定の `pytest` 実行では走らない
(pyproject.toml の addopts = "-m \"not live\"")。明示的に実行するには:

    pytest -m live

OPENAI_API_KEY が環境に見つからない場合は自動的に skip する。
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from big5_persona_chat import Big5, ChatSession, Persona, chat

load_dotenv()  # リポジトリルートの .env (OPENAI_API_KEY 等) を読み込む

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY が設定されていないため実APIテストをスキップ",
    ),
]

# pptx スライド3/4, README 記載の8プリセットの一部
EXTRAVERT_LEADER = Persona(
    big5=Big5(O=2, C=2, E=3, A=1, N=-2),
    biography_id=2,
    name="EXTRAVERT_LEADER",
)


def test_one_shot_chat_returns_real_reply():
    """pptx スライド3: 1ショット chat() の例。"""
    reply = chat(
        model="openai:gpt-4.1",
        language="ja",
        persona=EXTRAVERT_LEADER,
        text="休日のおすすめの過ごし方を教えて",
        max_tokens=60,
    )
    assert isinstance(reply, str)
    assert len(reply.strip()) > 0


def test_chat_session_multi_turn_returns_real_replies():
    """pptx スライド4: ChatSession によるマルチターン対話の例。"""
    session = ChatSession(
        model="openai:gpt-4.1",
        language="ja",
        persona=EXTRAVERT_LEADER,
        reinject_every=6,
        max_tokens=60,
    )

    reply1 = session.send("こんにちは")
    reply2 = session.send("自己紹介して")

    assert isinstance(reply1, str) and len(reply1.strip()) > 0
    assert isinstance(reply2, str) and len(reply2.strip()) > 0
    assert len(session.history) == 4

    session.reset()
    assert session.history == []
