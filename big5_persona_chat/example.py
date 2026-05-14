"""動作確認用デモ。

実行前に .env (OPENAI_API_KEY 等) を用意し、`pip install -e .` でパッケージを入れること。
"""

from __future__ import annotations

from dotenv import load_dotenv

from big5_persona_chat import Big5, ChatSession, Persona, chat


def demo_one_shot() -> None:
    """1ショット同期チャットの例。外向リーダー型(EXTRAVERT_LEADER)。"""
    persona = Persona(
        big5=Big5(O=2, C=2, E=3, A=1, N=-2),
        biography_id=4,
        name="EXTRAVERT_LEADER",
    )
    reply = chat(
        model="openai:gpt-4.1",
        language="ja",
        persona=persona,
        text="休日のおすすめの過ごし方を教えて",
        temperature=0.7,
    )
    print("=== EXTRAVERT_LEADER (ja, gpt-4.1) ===")
    print(reply)
    print()


def demo_multi_turn() -> None:
    """セッション(複数ターン)の例。内向思索家型(INTROVERT_THINKER)。"""
    persona = Persona(
        big5=Big5(O=3, C=2, E=-3, A=1, N=0),
        biography_id=11,
        name="INTROVERT_THINKER",
    )
    session = ChatSession(
        model="openai:gpt-4.1",
        language="ja",
        persona=persona,
        reinject_every=6,
    )
    print("=== INTROVERT_THINKER (ja, gpt-4.1) ===")
    for user_text in ["はじめまして", "最近読んだ本でおすすめは?", "週末はどう過ごしてる?"]:
        print(f"USER: {user_text}")
        print(f"BOT : {session.send(user_text)}")
        print()


def demo_same_persona_multi_lang() -> None:
    """同じ Persona を言語切り替えで使う例。神経質芸術家型(NEUROTIC_ARTIST)。"""
    persona = Persona(
        big5=Big5(O=3, C=-2, E=1, A=1, N=3),
        biography_id=7,
        name="NEUROTIC_ARTIST",
    )
    for lang in ("ja", "en"):
        reply = chat(
            model="openai:gpt-4.1",
            language=lang,
            persona=persona,
            text="今日の気分を一言で表すと?" if lang == "ja" else "Describe your mood today in one sentence.",
        )
        print(f"=== NEUROTIC_ARTIST ({lang}, gpt-4.1) ===")
        print(reply)
        print()


if __name__ == "__main__":
    load_dotenv()
    demo_one_shot()
    demo_multi_turn()
    demo_same_persona_multi_lang()
