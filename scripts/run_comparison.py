"""Head-to-head comparison: big5chat vs MPI vs PersonaLLM.

Runs the same persona(s) through all three methodologies and compares
Cohen's d effect sizes per Big5 dimension.

Usage:
    python scripts/run_comparison.py                    # default: 4-corner personas
    python scripts/run_comparison.py --n-personas 8     # sample more
    python scripts/run_comparison.py --model openai:gpt-4.1-mini   # cheaper test

Output:
    results/comparison_<timestamp>.json
    stdout table of per-method, per-dimension Cohen's d

Methodologies tested per persona:
    1. big5chat (Serapio-Garcia 9-stage Likert + 3-layer eval, BFI only here)
    2. MPI 120-item (neutral prompt OR Serapio-Garcia system prompt)
    3. PersonaLLM 44-item BFI (native persona prompt OR Serapio-Garcia)

The "apples-to-apples" fairness is that:
    - Same provider, same seed base, same temperature setting.
    - Same 4-8 persona profiles with known {H, L} poles per dimension.
    - Scoring re-implemented directly from each paper's original code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from big5chat.analysis.effect_size import effect_size_report
from big5chat.baselines.mpi import MPIEvaluator
from big5chat.baselines.personallm import PersonaLLMEvaluator, build_persona_description
from big5chat.dialogue.providers import get_provider
from big5chat.evaluation.bfi import BFIEvaluator
from big5chat.experiments.config import generate_32_profiles
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


DIMS = ["O", "C", "E", "A", "N"]


async def evaluate_persona_three_ways(
    spec: PersonaSpec,
    assembler: PromptAssembler,
    provider,
    mpi_inventory: str,
    skip_mpi: bool = False,
    skip_personallm: bool = False,
    seed_base: int = 42,
) -> dict[str, Any]:
    """Return dim means (normalized to 1..5 for BFI, 1..5 for MPI, per-item mean for PLLM)."""
    result: dict[str, Any] = {
        "profile_id": spec.profile_id,
        "persona_hash": spec.profile_hash(),
        "big5_input": spec.big5_values.as_dict(),
    }

    # --- 1) big5chat BFI ---
    bfi = BFIEvaluator(
        provider, assembler, postambles=[0], variants=["A"], n_reps=1,
        max_concurrency=8,
    )
    bfi_result = await bfi.evaluate(spec, seed_base=seed_base)
    result["big5chat"] = {
        "dim_mean_5pt": bfi_result.dim_scores,
        "dim_std": bfi_result.dim_std,
        "dim_n": bfi_result.dim_n,
    }

    # --- 2) MPI with big5chat Serapio-Garcia persona ---
    if not skip_mpi:
        mpi_eval = MPIEvaluator(
            provider,
            inventory_path=mpi_inventory,
            assembler=assembler,
            max_concurrency=8,
        )
        mpi_result = await mpi_eval.evaluate(spec, seed_base=seed_base)
        result["mpi"] = {
            "dim_mean_5pt": mpi_result.dim_mean,
            "dim_std": mpi_result.dim_std,
            "dim_n": mpi_result.dim_n,
            "choice_counts": mpi_result.choice_counts,
        }

    # --- 3) PersonaLLM native persona phrasing (paper's original method) ---
    if not skip_personallm:
        pllm_eval = PersonaLLMEvaluator(provider)
        pllm_result = await pllm_eval.evaluate(
            persona_spec=spec,
            mode="personallm_native",
            seed_base=seed_base,
        )
        result["personallm_native"] = {
            "dim_mean_5pt": pllm_result.dim_mean,
            "dim_sum": pllm_result.dim_sum,
            "dim_n": pllm_result.dim_n,
            "persona_phrase": build_persona_description(spec.big5_values),
        }

        # Variant: PersonaLLM items but with big5chat's richer system prompt
        pllm_hybrid = await pllm_eval.evaluate(
            persona_spec=spec,
            mode="big5chat_persona",
            assembler=assembler,
            seed_base=seed_base,
        )
        result["personallm_hybrid"] = {
            "dim_mean_5pt": pllm_hybrid.dim_mean,
            "dim_sum": pllm_hybrid.dim_sum,
            "dim_n": pllm_hybrid.dim_n,
        }

    return result


def compute_cohens_d_per_method(
    persona_results: list[dict[str, Any]],
    method_key: str,
) -> dict[str, dict[str, float]]:
    """For each Big5 dim, compute d between profiles with high vs low value on that dim."""
    out: dict[str, dict[str, float]] = {}
    for dim in DIMS:
        high_scores: list[float] = []
        low_scores: list[float] = []
        for rec in persona_results:
            if method_key not in rec:
                continue
            scores = rec[method_key].get("dim_mean_5pt", {})
            score = scores.get(dim)
            if score is None or score != score:  # NaN check
                continue
            val = rec["big5_input"][dim]
            if val > 3:
                high_scores.append(score)
            elif val < 3:
                low_scores.append(score)
        if len(high_scores) >= 2 and len(low_scores) >= 2:
            out[dim] = effect_size_report(high_scores, low_scores, n_boot=1000)
        else:
            out[dim] = {"error": "insufficient data", "n_high": len(high_scores), "n_low": len(low_scores)}
    return out


def sample_personas(n: int, language: str = "ja") -> list[PersonaSpec]:
    """Return n persona specs distributed across the 2^5 binary profile space."""
    profiles = generate_32_profiles(language=language, amplitude=2)
    if n >= len(profiles):
        return [p.to_persona_spec() for p in profiles]
    # Strided selection for balanced coverage of {+,-} per dim
    step = max(1, len(profiles) // n)
    selected = profiles[::step][:n]
    return [p.to_persona_spec() for p in selected]


async def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-personas", type=int, default=4)
    parser.add_argument("--model", default="openai:gpt-4.1")
    parser.add_argument("--language", default="ja", choices=["ja", "en", "zh"])
    parser.add_argument("--mpi-inventory", default="external/MPI/inventories/mpi_120.csv")
    parser.add_argument("--skip-mpi", action="store_true")
    parser.add_argument("--skip-personallm", action="store_true")
    parser.add_argument("--seed-base", type=int, default=42)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    # MPI / PersonaLLM items are English-only. If language=ja, only big5chat is bilingual.
    if args.language == "ja" and not args.skip_mpi:
        print("[warn] MPI inventory is English-only. big5chat persona is in Japanese; "
              "the inventory items will still be in English. For pure JA comparison, "
              "use --skip-mpi --skip-personallm.")

    provider = get_provider(args.model)
    assembler = PromptAssembler()
    personas = sample_personas(args.n_personas, args.language)

    print(f"Running comparison on {len(personas)} personas with {args.model}")
    persona_results: list[dict[str, Any]] = []
    for i, spec in enumerate(personas, 1):
        t0 = time.perf_counter()
        print(f"  [{i}/{len(personas)}] {spec.profile_id} ", end="", flush=True)
        rec = await evaluate_persona_three_ways(
            spec, assembler, provider,
            mpi_inventory=args.mpi_inventory,
            skip_mpi=args.skip_mpi,
            skip_personallm=args.skip_personallm,
            seed_base=args.seed_base,
        )
        persona_results.append(rec)
        print(f"({time.perf_counter() - t0:.1f}s)")

    # Compute per-method Cohen's d
    method_keys = ["big5chat"]
    if not args.skip_mpi: method_keys.append("mpi")
    if not args.skip_personallm:
        method_keys.append("personallm_native")
        method_keys.append("personallm_hybrid")

    method_effects = {
        m: compute_cohens_d_per_method(persona_results, m) for m in method_keys
    }

    # Pretty-print
    print()
    print("=" * 78)
    header = f"{'Dim':<4} " + "  ".join(f"{m:<22}" for m in method_keys)
    print(header)
    print("-" * len(header))
    for dim in DIMS:
        row = f"{dim:<4} "
        for m in method_keys:
            es = method_effects[m][dim]
            if "cohens_d" in es:
                marker = "✓" if es["meets_threshold"] else " "
                row += f"d={es['cohens_d']:+.2f} [{es['ci_95_lo']:+.2f},{es['ci_95_hi']:+.2f}]{marker}  "
            else:
                row += f"{'n/a':<23}  "
        print(row)
    print("=" * 78)

    # Save
    out_path = Path(args.out) if args.out else Path(f"results/comparison_{int(time.time())}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "n_personas": args.n_personas,
            "model": args.model,
            "language": args.language,
            "seed_base": args.seed_base,
            "skip_mpi": args.skip_mpi,
            "skip_personallm": args.skip_personallm,
        },
        "persona_results": persona_results,
        "effect_sizes_per_method": method_effects,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
