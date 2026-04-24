"""Tests for dialogue reinjection + compression."""

from big5chat.dialogue.reinjector import PersonaReinjector


def test_should_reinject_cadence():
    r = PersonaReinjector(interval=5)
    assert not r.should_reinject(0)
    assert not r.should_reinject(1)
    assert not r.should_reinject(4)
    assert r.should_reinject(5)
    assert r.should_reinject(10)
    assert not r.should_reinject(6)


def test_prepare_messages_basic():
    r = PersonaReinjector(interval=5, compress_at=100)
    history = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
    ]
    msgs = r.prepare_messages(
        system_prompt="SYSTEM",
        history=history,
        new_user_msg="hello",
        turn_idx=1,
    )
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "SYSTEM"
    assert msgs[-1] == {"role": "user", "content": "hello"}
    assert len(msgs) == 4  # system + 2 history + user


def test_prepare_messages_with_reinjection():
    r = PersonaReinjector(interval=5)
    history = [{"role": "user", "content": f"u{i}"} for i in range(10)]
    msgs = r.prepare_messages(
        system_prompt="SYS",
        history=history,
        new_user_msg="u5",
        turn_idx=5,
        reinjection_text="REMIND",
    )
    # Reminder should appear just before the new user message.
    reminder_pos = next(i for i, m in enumerate(msgs) if m["content"] == "REMIND")
    assert msgs[reminder_pos]["role"] == "system"
    assert reminder_pos == len(msgs) - 2


def test_prepare_messages_with_compression():
    r = PersonaReinjector(interval=5, compress_at=6, compress_keep_recent=2)
    history = [{"role": "user", "content": f"u{i}"} for i in range(8)]
    msgs = r.prepare_messages(
        system_prompt="SYS",
        history=history,
        new_user_msg="new",
        turn_idx=1,
        summary_of_old_turns="SUMMARY",
    )
    # Should have compressed past-history to summary; keep 2 recent.
    assert any("SUMMARY" in m.get("content", "") for m in msgs)
    kept = [m for m in msgs if m["role"] == "user" and m["content"].startswith("u")]
    assert len(kept) == 2
