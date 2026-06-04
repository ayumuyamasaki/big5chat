"""CLI entry points wired up in pyproject.toml [project.scripts]."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from big5chat.dialogue.providers import get_provider
from big5chat.dialogue.runner import DialogueRunner
from big5chat.evaluation.bfi import BFIEvaluator
from big5chat.evaluation.trait_mcq import TraitMCQEvaluator
from big5chat.experiments.config import ExperimentConfig, PersonaConfig
from big5chat.journal import JsonlJournal
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler
from big5chat.safety.constraints import safety_preamble


def _load_env():
    load_dotenv()


def _parse_big5(arg: str) -> Big5Values:
    """Parse 'O=+3,C=-2,E=+3,A=+2,N=-2' format."""
    parts = {}
    for p in arg.replace(" ", "").split(","):
        if "=" not in p:
            raise argparse.ArgumentTypeError(f"Invalid big5 token: {p}")
        k, v = p.split("=")
        parts[k] = int(v)
    return Big5Values(**parts)


def interactive_chat() -> None:
    """big5-chat: launch an interactive terminal chat with a persona."""
    _load_env()
    parser = argparse.ArgumentParser(
        description="Interactive chat with a Big5 persona."
    )
    parser.add_argument(
        "--big5",
        type=_parse_big5,
        default=_parse_big5("O=3,C=-1,E=3,A=2,N=-2"),
        help="Big5 values, e.g. 'O=3,C=-1,E=3,A=2,N=-2'",
    )
    parser.add_argument("--model", default=os.environ.get("BIG5_DEFAULT_MODEL", "openai:gpt-4.1"))
    parser.add_argument("--language", default="ja", choices=["ja", "en", "zh"])
    parser.add_argument("--bio-id", type=int, default=0)
    parser.add_argument("--profile-id", default="interactive")
    parser.add_argument("--show-system", action="store_true",
                        help="Print the system prompt before chatting.")
    parser.add_argument("--log", default=None, help="Optional JSONL log path.")
    args = parser.parse_args()

    spec = PersonaSpec(
        profile_id=args.profile_id,
        big5_values=args.big5,
        biographic_description_id=args.bio_id,
        item_postamble_id=0,
        prompt_variant="A",
        language=args.language,
    )
    asyncio.run(_chat_loop(spec, args))


async def _chat_loop(spec: PersonaSpec, args) -> None:
    provider = get_provider(args.model)
    assembler = PromptAssembler()
    preamble = safety_preamble(spec.big5_values, spec.language)
    runner = DialogueRunner(
        provider=provider,
        assembler=assembler,
        persona_spec=spec,
        safety_preamble=preamble,
    )
    if args.show_system:
        print("=" * 60)
        print("SYSTEM PROMPT")
        print("=" * 60)
        print(runner.system_prompt)
        print("=" * 60)

    journal = None
    if args.log:
        journal = JsonlJournal(args.log, experiment_id=spec.profile_id)

    print(f"\n[Persona: {spec.profile_id} | {spec.big5_values.as_dict()}]")
    print("対話を開始します。終了は /quit")
    try:
        while True:
            try:
                user = input("\nあなた> ").strip()
            except EOFError:
                break
            if not user:
                continue
            if user in ("/quit", "/exit"):
                break
            turn = await runner.send(user)
            print(f"\nbot[{turn.turn_idx}]> {turn.assistant}")
            if journal:
                journal.log_turn(
                    persona_spec=spec,
                    messages=[
                        {"role": "system", "content": runner.system_prompt},
                        *runner.history[:-1],
                        {"role": "user", "content": user},
                    ],
                    response=turn.response,
                    turn_idx=turn.turn_idx,
                )
    finally:
        if journal:
            journal.close()


def evaluate_single() -> None:
    """big5-evaluate: run BFI + TRAIT on one persona."""
    _load_env()
    parser = argparse.ArgumentParser(description="Evaluate a single persona.")
    parser.add_argument("--big5", type=_parse_big5, required=True)
    parser.add_argument("--model", default=os.environ.get("BIG5_DEFAULT_MODEL", "openai:gpt-4.1"))
    parser.add_argument("--language", default="ja", choices=["ja", "en", "zh"])
    parser.add_argument("--bio-id", type=int, default=0)
    parser.add_argument("--profile-id", default="eval_single")
    parser.add_argument("--n-reps", type=int, default=1)
    parser.add_argument("--out", default="results/eval_single.json")
    parser.add_argument("--skip-trait", action="store_true")
    args = parser.parse_args()

    spec = PersonaSpec(
        profile_id=args.profile_id,
        big5_values=args.big5,
        biographic_description_id=args.bio_id,
        item_postamble_id=0,
        prompt_variant="A",
        language=args.language,
    )
    asyncio.run(_evaluate_single(spec, args))


async def _evaluate_single(spec: PersonaSpec, args) -> None:
    provider = get_provider(args.model)
    assembler = PromptAssembler()
    bfi = BFIEvaluator(provider, assembler, n_reps=args.n_reps, max_concurrency=8,
                       items_filename="bfi_ja.json")
    bfi_result = await bfi.evaluate(spec)
    payload = {
        "profile_id": spec.profile_id,
        "persona_hash": spec.profile_hash(),
        "big5_input": spec.big5_values.as_dict(),
        "bfi": bfi_result.to_dict(),
    }
    if not args.skip_trait:
        trait = TraitMCQEvaluator(provider, assembler, max_concurrency=8)
        trait_result = await trait.evaluate(spec)
        payload["trait"] = {
            "dim_scores_01": trait_result.dim_scores,
            "dim_scores_5pt": trait_result.dim_scores_5point(),
        }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"BFI dim scores: {bfi_result.dim_scores}")
    if "trait" in payload:
        print(f"TRAIT dim scores (5pt): {payload['trait']['dim_scores_5pt']}")


def run_pilot() -> None:
    """big5-pilot: run a full Phase-0 pilot from a YAML config."""
    _load_env()
    parser = argparse.ArgumentParser(description="Run Phase-0 pilot experiment.")
    parser.add_argument("--config", required=True, help="Path to experiment YAML.")
    args = parser.parse_args()

    config = ExperimentConfig.from_yaml(args.config)
    from big5chat.experiments.protocol import run_experiment
    payload = asyncio.run(run_experiment(config))
    print(f"Pilot complete. Results written to {config.output_dir}/")
    for dim, es in payload["effect_sizes"].items():
        if "cohens_d" in es:
            marker = "✓" if es["meets_threshold"] else "✗"
            print(f"  [{dim}] Cohen's d = {es['cohens_d']:.2f} {marker}")


if __name__ == "__main__":
    # Dispatch by first arg if run as `python -m big5chat.cli <subcmd>`
    if len(sys.argv) < 2:
        print("Usage: python -m big5chat.cli {chat|evaluate|pilot} [args]")
        sys.exit(1)
    cmd = sys.argv.pop(1)
    if cmd == "chat":
        interactive_chat()
    elif cmd == "evaluate":
        evaluate_single()
    elif cmd == "pilot":
        run_pilot()
    else:
        print(f"Unknown subcommand: {cmd}")
        sys.exit(1)
