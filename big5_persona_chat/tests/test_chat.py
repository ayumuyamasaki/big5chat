"""chat / achat / chat_raw / achat_raw / ChatSession のロジック検証。

LLM 呼び出し自体は mock_get_provider フィクスチャで差し替え、ネットワーク・
APIキー無しで big5_persona_chat.chat モジュールの配線を検証する。
"""

from __future__ import annotations

import pytest

from big5_persona_chat import ChatSession, achat, achat_raw, chat, chat_raw


def test_chat_returns_mock_content(mock_get_provider, extravert_leader):
    mock_get_provider.next_response = "こんにちは、休日はキャンプがおすすめです！"
    reply = chat(
        model="openai:gpt-4.1",
        language="ja",
        persona=extravert_leader,
        text="休日のおすすめの過ごし方を教えて",
    )
    assert reply == "こんにちは、休日はキャンプがおすすめです！"
    assert len(mock_get_provider.calls) == 1
    sent_messages = mock_get_provider.calls[0]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[1] == {"role": "user", "content": "休日のおすすめの過ごし方を教えて"}


def test_chat_raw_returns_meta(mock_get_provider, extravert_leader):
    mock_get_provider.next_response = "raw response"
    reply = chat_raw(
        model="openai:gpt-4.1",
        language="ja",
        persona=extravert_leader,
        text="hi",
    )
    assert reply.content == "raw response"
    assert reply.provider == "mock"
    assert reply.model_id == "mock-model"
    assert reply.output_tokens == len("raw response")


@pytest.mark.asyncio
async def test_achat_returns_mock_content(mock_get_provider, extravert_leader):
    mock_get_provider.next_response = "async response"
    reply = await achat(
        model="openai:gpt-4.1",
        language="ja",
        persona=extravert_leader,
        text="hi",
    )
    assert reply == "async response"


@pytest.mark.asyncio
async def test_achat_raw_returns_meta(mock_get_provider, extravert_leader):
    reply = await achat_raw(
        model="openai:gpt-4.1",
        language="en",
        persona=extravert_leader,
        text="hi",
    )
    assert reply.provider == "mock"


@pytest.mark.asyncio
async def test_chat_raises_runtime_error_inside_running_loop(mock_get_provider, extravert_leader):
    # chat.py の _no_running_loop_or_raise: 同期版を実行中イベントループ内から
    # 呼ぶと明示的な RuntimeError になる (非同期版を使うよう案内するため)。
    with pytest.raises(RuntimeError):
        chat(model="openai:gpt-4.1", language="ja", persona=extravert_leader, text="hi")


def test_chat_same_persona_different_language_changes_system_prompt(
    mock_get_provider, extravert_leader
):
    chat(model="openai:gpt-4.1", language="ja", persona=extravert_leader, text="hi")
    chat(model="openai:gpt-4.1", language="en", persona=extravert_leader, text="hi")
    ja_system = mock_get_provider.calls[0]["messages"][0]["content"]
    en_system = mock_get_provider.calls[1]["messages"][0]["content"]
    assert ja_system != en_system


def test_chat_session_history_accumulates_and_reset_clears_it(
    mock_get_provider, introvert_thinker
):
    mock_get_provider.response_queue = ["はじめまして", "本が好きです"]
    session = ChatSession(model="openai:gpt-4.1", language="ja", persona=introvert_thinker)

    reply1 = session.send("はじめまして")
    reply2 = session.send("最近読んだ本でおすすめは?")

    assert reply1 == "はじめまして"
    assert reply2 == "本が好きです"
    assert session.history == [
        {"role": "user", "content": "はじめまして"},
        {"role": "assistant", "content": "はじめまして"},
        {"role": "user", "content": "最近読んだ本でおすすめは?"},
        {"role": "assistant", "content": "本が好きです"},
    ]
    assert session.system_prompt  # 組み立て済みシステムプロンプトが取得できる

    session.reset()
    assert session.history == []
    # system_prompt はリセット後も保持される
    assert session.system_prompt


@pytest.mark.asyncio
async def test_chat_session_asend(mock_get_provider, extravert_leader):
    mock_get_provider.next_response = "async session reply"
    session = ChatSession(model="openai:gpt-4.1", language="ja", persona=extravert_leader)
    reply = await session.asend("こんにちは")
    assert reply == "async session reply"
    assert len(session.history) == 2


def test_chat_session_reinject_every_inserts_reminder_at_boundary(
    mock_get_provider, extravert_leader
):
    mock_get_provider.response_queue = ["r1", "r2", "r3"]
    session = ChatSession(
        model="openai:gpt-4.1",
        language="ja",
        persona=extravert_leader,
        reinject_every=2,
    )

    session.send("turn1")
    session.send("turn2")
    session.send("turn3")  # turn_count が 2 (>0 かつ 2%2==0) の時点で送信 -> 再注入対象

    calls = mock_get_provider.calls
    assert len(calls) == 3

    # 1, 2 ターン目は再注入なし: [system, ...history, user]
    assert calls[0]["messages"][-1] == {"role": "user", "content": "turn1"}
    assert all(m["role"] != "system" for m in calls[0]["messages"][1:])
    assert calls[1]["messages"][-1] == {"role": "user", "content": "turn2"}

    # 3ターン目: 直前に system ロールの再注入メッセージが挿入される
    third_call_messages = calls[2]["messages"]
    assert third_call_messages[-1] == {"role": "user", "content": "turn3"}
    reinject_msg = third_call_messages[-2]
    assert reinject_msg["role"] == "system"
    assert "思い出してください" in reinject_msg["content"]


def test_chat_session_without_reinject_every_never_inserts_reminder(
    mock_get_provider, extravert_leader
):
    mock_get_provider.response_queue = ["r1", "r2", "r3", "r4"]
    session = ChatSession(model="openai:gpt-4.1", language="ja", persona=extravert_leader)
    for i in range(4):
        session.send(f"turn{i}")
    for call in mock_get_provider.calls:
        assert all(m["role"] != "system" for m in call["messages"][1:])
