"""DialogueRunner: orchestrates multi-turn persona-driven conversations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from big5chat.dialogue.providers.base import LLMProvider, LLMResponse
from big5chat.dialogue.reinjector import PersonaReinjector, build_summary_prompt
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


@dataclass
class DialogueTurn:
    """A single exchange: user utterance + assistant response."""

    turn_idx: int
    user: str
    assistant: str
    response: LLMResponse
    elapsed_ms: int
    reinjected: bool = False


@dataclass
class DialogueRunner:
    """Runs a multi-turn dialogue with persona re-injection.

    Usage:
        >>> runner = DialogueRunner(provider, assembler, persona_spec)
        >>> turn1 = await runner.send("こんにちは")
        >>> turn2 = await runner.send("週末の予定を教えて")
    """

    provider: LLMProvider
    assembler: PromptAssembler
    persona_spec: PersonaSpec
    reinjector: PersonaReinjector = field(default_factory=PersonaReinjector)
    temperature: float = 0.7
    top_p: float = 0.95
    max_tokens: int = 400
    safety_preamble: str | None = None
    seed_base: int | None = 42
    on_turn: Callable[[DialogueTurn], None] | None = None
    summarizer: Callable[[list[dict[str, str]]], str] | None = None

    def __post_init__(self):
        self._system_prompt = self.assembler.assemble(
            self.persona_spec, safety_preamble=self.safety_preamble
        )
        self._history: list[dict[str, str]] = []
        self._turn_idx = 0
        self._summary: str | None = None

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def history(self) -> list[dict[str, str]]:
        return list(self._history)

    @property
    def turn_count(self) -> int:
        return self._turn_idx

    def reset(self) -> None:
        self._history = []
        self._turn_idx = 0
        self._summary = None

    async def send(self, user_msg: str) -> DialogueTurn:
        """Send a user message; return the assistant response turn."""
        # Prepare summary if needed
        if (
            len(self._history) >= self.reinjector.compress_at
            and self._summary is None
            and self.summarizer is not None
        ):
            old = self._history[: -self.reinjector.compress_keep_recent]
            self._summary = self.summarizer(old)

        reinject_text = None
        will_reinject = self.reinjector.should_reinject(self._turn_idx)
        if will_reinject:
            reinject_text = self.assembler.reinjection_message(self.persona_spec)

        messages = self.reinjector.prepare_messages(
            system_prompt=self._system_prompt,
            history=self._history,
            new_user_msg=user_msg,
            turn_idx=self._turn_idx,
            reinjection_text=reinject_text,
            summary_of_old_turns=self._summary,
        )

        t0 = time.perf_counter()
        seed = (self.seed_base + self._turn_idx) if self.seed_base is not None else None
        response = await self.provider.complete(
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            seed=seed if self.provider.supports_seed else None,
            max_tokens=self.max_tokens,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)

        # Persist turn in history
        self._history.append({"role": "user", "content": user_msg})
        self._history.append({"role": "assistant", "content": response.content})

        turn = DialogueTurn(
            turn_idx=self._turn_idx,
            user=user_msg,
            assistant=response.content,
            response=response,
            elapsed_ms=elapsed,
            reinjected=will_reinject,
        )
        self._turn_idx += 1
        if self.on_turn:
            self.on_turn(turn)
        return turn
