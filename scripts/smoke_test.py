"""End-to-end smoke test: persona -> prompt -> LLM call -> BFI parsing.

Use this to verify your API key + all wiring without spending much.
Runs 1 persona x reduced BFI items x 1 rep only.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from big5chat.dialogue.providers import get_provider
from big5chat.evaluation.bfi import BFIEvaluator
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


async def main() -> int:
    load_dotenv()

    if not any(
        os.environ.get(k)
        for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
    ):
        print("[smoke_test] No API key in environment. Set at least one.")
        return 1

    model = os.environ.get("BIG5_DEFAULT_MODEL", "openai:gpt-4.1")
    try:
        provider = get_provider(model)
    except Exception as e:
        print(f"[smoke_test] Provider init failed for {model}: {e}")
        return 1

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", default="ja", choices=["ja", "en", "zh"])
    ap_args, _ = ap.parse_known_args()
    spec = PersonaSpec(
        profile_id=f"smoke_test_highE_{ap_args.language}",
        big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0,
        item_postamble_id=0,
        prompt_variant="A",
        language=ap_args.language,
    )

    assembler = PromptAssembler()
    print("=" * 70)
    print("SYSTEM PROMPT:")
    print("=" * 70)
    print(assembler.assemble(spec))
    print("=" * 70)

    # 1-turn dialogue test (localized user prompt)
    user_prompts = {
        "ja": "週末の予定を1文で教えてください。",
        "en": "Tell me your weekend plan in one sentence.",
        "zh": "请用一句话告诉我你周末的计划。",
    }
    resp = await provider.complete(
        messages=[
            {"role": "system", "content": assembler.assemble(spec)},
            {"role": "user", "content": user_prompts[spec.language]},
        ],
        temperature=0.7,
        seed=42 if provider.supports_seed else None,
        max_tokens=120,
    )
    print(f"\n[DIALOGUE RESPONSE]\n{resp.content}\n")
    print(f"Tokens: input={resp.input_tokens}, output={resp.output_tokens}")

    # Mini BFI (only the default 20 items, no repetition)
    bfi = BFIEvaluator(
        provider,
        assembler,
        postambles=[0],
        variants=["A"],
        n_reps=1,
        max_concurrency=8,
    )
    print("\nRunning reduced BFI (20 items, 1 config)...")
    result = await bfi.evaluate(spec, seed_base=42)
    print("\nBFI DIM SCORES (1-5 scale):")
    for dim in ["O", "C", "E", "A", "N"]:
        mean = result.dim_scores[dim]
        n = result.dim_n[dim]
        target = getattr(spec.big5_values, dim)
        # Expected direction marker
        expected_hi = target > 0
        actual_hi = mean > 3.0
        match = "✓" if expected_hi == actual_hi else "✗"
        print(f"  [{dim}] mean={mean:.2f} (n={n}) target={target:+d} {match}")

    print("\n[smoke_test] OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
