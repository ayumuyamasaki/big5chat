"""Persona re-injection and summary compression (ConstructionPlan §F).

Three-layer defense against identity drift:
1. System prompt always resent (handled by provider, not here).
2. Inline reminder every N turns (default 5).
3. Summary compression when history exceeds threshold (default 20 turns).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaReinjector:
    """Inject persona reminders and compress history.

    Attributes:
        interval: Re-inject persona reminder every `interval` turns.
        compress_at: Trigger history summarization once history >= this many
            messages (user+assistant turns combined, excluding the system prompt).
        compress_keep_recent: How many recent messages to keep verbatim when
            compressing older history.
    """

    interval: int = 5
    compress_at: int = 20
    compress_keep_recent: int = 10

    def should_reinject(self, turn_idx: int) -> bool:
        """Should we append a re-injection reminder after turn `turn_idx`?"""
        return turn_idx > 0 and turn_idx % self.interval == 0

    def prepare_messages(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        new_user_msg: str,
        turn_idx: int,
        reinjection_text: str | None = None,
        summary_of_old_turns: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the full message list for the next LLM call.

        Args:
            system_prompt: The persona system prompt (unchanged per turn).
            history: List of prior {role, content} messages (user/assistant
                alternating, no system entries).
            new_user_msg: The new user input for this turn.
            turn_idx: 0-indexed turn counter. Re-injection triggers at
                turn_idx % interval == 0 AND turn_idx > 0.
            reinjection_text: Text of reminder to inject when due. Required
                when `should_reinject(turn_idx)` is true.
            summary_of_old_turns: When history length >= compress_at, a
                pre-computed summary to replace the older portion. Typically
                produced by an auxiliary LLM call.
        """
        msgs: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        effective_history = history
        if len(history) >= self.compress_at and summary_of_old_turns is not None:
            keep = self.compress_keep_recent
            msgs.append(
                {
                    "role": "system",
                    "content": f"[これまでの会話の要約] {summary_of_old_turns}",
                }
            )
            effective_history = history[-keep:]

        msgs.extend(effective_history)

        if self.should_reinject(turn_idx) and reinjection_text:
            msgs.append({"role": "system", "content": reinjection_text})

        msgs.append({"role": "user", "content": new_user_msg})
        return msgs


def build_summary_prompt(old_history: list[dict[str, str]], persona_summary: str) -> str:
    """Return a prompt that asks an LLM to summarize history while preserving
    the assistant's persona.

    This is passed to a lightweight summarization model (e.g., gpt-4.1-mini).
    """
    transcript = "\n".join(
        f"[{m['role']}] {m['content']}" for m in old_history
    )
    return (
        "次の会話の要約を200字以内で作成してください。"
        "応答者のペルソナ（以下）は会話中ずっと不変であることを前提とし、"
        "人物像が曖昧化しないように事実と情緒の両面を保ってください。\n\n"
        f"【応答者ペルソナ】{persona_summary}\n\n"
        "【会話ログ】\n"
        f"{transcript}\n\n"
        "【要約】"
    )
