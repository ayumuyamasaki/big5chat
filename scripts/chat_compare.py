"""Interactive chat across all three persona-induction methodologies.

Lets you talk to a persona driven by big5chat / MPI P^2 / PersonaLLM binary
prompts and compare responses side-by-side or one-at-a-time.

Usage:
    # Single-method chat (one method at a time)
    python scripts/chat_compare.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --mode big5chat
    python scripts/chat_compare.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --mode mpi
    python scripts/chat_compare.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --mode personallm

    # Side-by-side mode (every message goes to all three, responses shown together)
    python scripts/chat_compare.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --mode all

    # Show system prompts before chatting (useful for inspection)
    python scripts/chat_compare.py --big5 "O=3,C=3,E=3,A=3,N=3" --mode all --show-prompts

Commands during chat:
    /quit           exit
    /reset          clear history on all methods
    /history        print current conversation history
    /system         print the active system prompt(s)
    /switch <m>     switch single-method chat to m (big5chat|mpi|personallm)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from big5chat.baselines.prompts import (
    METHOD_LABELS,
    build_mpi_p2_prompt,
    build_personallm_prompt,
)
from big5chat.dialogue.providers import get_provider
from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


METHODS = ("big5chat", "mpi", "personallm")


def parse_big5(arg: str) -> Big5Values:
    parts = {}
    for p in arg.replace(" ", "").split(","):
        if "=" not in p:
            raise argparse.ArgumentTypeError(f"Invalid big5 token: {p}")
        k, v = p.split("=")
        parts[k] = int(v)
    return Big5Values(**parts)


@dataclass
class ChatSession:
    """Per-method conversation state."""

    method: str
    system_prompt: str
    provider: LLMProvider
    history: list[dict[str, str]] = field(default_factory=list)
    turn_idx: int = 0

    async def send(self, user_msg: str, seed_base: int = 42) -> str:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_msg})
        resp = await self.provider.complete(
            messages=messages,
            temperature=0.7,
            top_p=0.95,
            seed=(seed_base + self.turn_idx) if self.provider.supports_seed else None,
            max_tokens=400,
        )
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": resp.content})
        self.turn_idx += 1
        return resp.content

    def reset(self) -> None:
        self.history.clear()
        self.turn_idx = 0


def build_sessions(
    spec: PersonaSpec,
    provider: LLMProvider,
    methods: list[str],
) -> dict[str, ChatSession]:
    assembler = PromptAssembler()
    sessions: dict[str, ChatSession] = {}
    for m in methods:
        if m == "big5chat":
            system = assembler.assemble(spec)
        elif m == "mpi":
            system = build_mpi_p2_prompt(spec.big5_values)
        elif m == "personallm":
            system = build_personallm_prompt(spec.big5_values)
        else:
            raise ValueError(f"Unknown method: {m}")
        sessions[m] = ChatSession(method=m, system_prompt=system, provider=provider)
    return sessions


def _print_header(title: str) -> None:
    print("=" * 70)
    print(title)
    print("=" * 70)


def _print_system_prompts(sessions: dict[str, ChatSession]) -> None:
    for m, sess in sessions.items():
        _print_header(f"[{m.upper()}] SYSTEM PROMPT ({len(sess.system_prompt)} chars)")
        print(sess.system_prompt)
        print()


async def _send_to_all(
    sessions: dict[str, ChatSession],
    user_msg: str,
) -> dict[str, str]:
    tasks = {m: asyncio.create_task(sess.send(user_msg)) for m, sess in sessions.items()}
    results: dict[str, str] = {}
    for m, t in tasks.items():
        try:
            results[m] = await t
        except Exception as e:
            results[m] = f"[ERROR] {type(e).__name__}: {e}"
    return results


async def _single_mode_loop(
    sessions: dict[str, ChatSession],
    initial_method: str,
) -> None:
    current = initial_method
    print(f"\n[MODE=single] アクティブ手法: {current}")
    print("コマンド: /quit /reset /history /system /switch <m>")

    while True:
        try:
            user = input(f"\nあなた[{current}]> ").strip()
        except EOFError:
            break
        if not user:
            continue
        if user in ("/quit", "/exit"):
            break
        if user == "/reset":
            for sess in sessions.values():
                sess.reset()
            print("[all sessions reset]")
            continue
        if user == "/history":
            sess = sessions[current]
            for msg in sess.history:
                print(f"  [{msg['role']}] {msg['content'][:100]}...")
            continue
        if user == "/system":
            print(sessions[current].system_prompt)
            continue
        if user.startswith("/switch "):
            new = user.split(" ", 1)[1].strip()
            if new not in sessions:
                print(f"[unknown method: {new}. available: {list(sessions)}]")
            else:
                current = new
                print(f"[switched to {current} — history preserved per method]")
            continue

        reply = await sessions[current].send(user)
        print(f"\n{current}-bot> {reply}")


async def _all_mode_loop(sessions: dict[str, ChatSession]) -> None:
    print("\n[MODE=all] 3手法を並列実行、同じ入力に3応答が返ります。")
    print("コマンド: /quit /reset /history /system")

    while True:
        try:
            user = input("\nあなた> ").strip()
        except EOFError:
            break
        if not user:
            continue
        if user in ("/quit", "/exit"):
            break
        if user == "/reset":
            for sess in sessions.values():
                sess.reset()
            print("[all sessions reset]")
            continue
        if user == "/history":
            for m, sess in sessions.items():
                print(f"--- {m} ({len(sess.history)//2} turns) ---")
                for msg in sess.history[-6:]:  # last 3 exchanges
                    print(f"  [{msg['role']}] {msg['content'][:100]}...")
            continue
        if user == "/system":
            _print_system_prompts(sessions)
            continue

        results = await _send_to_all(sessions, user)
        for m, reply in results.items():
            print(f"\n--- [{m}] ---")
            print(reply)


async def main_async(args) -> None:
    provider = get_provider(args.model)

    spec = PersonaSpec(
        profile_id=args.profile_id,
        big5_values=args.big5,
        biographic_description_id=args.bio_id,
        item_postamble_id=0,
        prompt_variant="A",
        language=args.language,
    )

    if args.mode == "all":
        methods = list(METHODS)
    else:
        methods = [args.mode]

    sessions = build_sessions(spec, provider, methods)

    # Header
    print(f"Model:     {args.model}")
    print(f"Persona:   {spec.profile_id}  {spec.big5_values.as_dict()}")
    print(f"Language:  {args.language}")
    print(f"Methods:   {', '.join(methods)}")
    for m in methods:
        print(f"  - {m}: {METHOD_LABELS[m]}")

    if args.language == "ja" and ("mpi" in methods or "personallm" in methods):
        print()
        print("[NOTE] MPI / PersonaLLM は英語ペルソナ定義のため、応答も英語になる傾向があります。")
        print("       日本語ペルソナのみで比較したい場合は --language en を避けて --mode big5chat を使用してください。")

    if args.show_prompts:
        print()
        _print_system_prompts(sessions)

    if args.mode == "all":
        await _all_mode_loop(sessions)
    else:
        await _single_mode_loop(sessions, args.mode)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Chat with a Big5 persona under each methodology.")
    parser.add_argument("--big5", type=parse_big5, required=True,
                        help="Big5 values, e.g. 'O=3,C=-1,E=3,A=2,N=-2'")
    parser.add_argument("--mode", choices=[*METHODS, "all"], default="all",
                        help="Which methodology to drive the persona. 'all' sends each message to all three.")
    parser.add_argument("--model", default=os.environ.get("BIG5_DEFAULT_MODEL", "openai:gpt-4.1"))
    parser.add_argument("--language", default="ja", choices=["ja", "en", "zh"],
                        help="Language of the big5chat system prompt (MPI/PersonaLLM are always English).")
    parser.add_argument("--bio-id", type=int, default=0)
    parser.add_argument("--profile-id", default="chat_compare")
    parser.add_argument("--show-prompts", action="store_true",
                        help="Print every active system prompt before chatting.")
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
