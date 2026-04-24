"""Run the 32-type binary pilot using auto-generated profiles.

Usage:
    python scripts/run_pilot_32.py --limit 8
    python scripts/run_pilot_32.py          # full 32 profiles
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from big5chat.experiments.config import (
    ExperimentConfig,
    generate_32_profiles,
)
from big5chat.experiments.protocol import run_experiment


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=32, help="Use only first N profiles.")
    parser.add_argument(
        "--base-config",
        default="configs/personas/phase0_pilot_32types.yaml",
        help="Base YAML for experiment-level params.",
    )
    parser.add_argument("--model", default=None, help="Override primary_model.")
    parser.add_argument("--skip-er", action="store_true", default=True)
    args = parser.parse_args()

    config = ExperimentConfig.from_yaml(args.base_config)
    config.personas = generate_32_profiles(language=config.language)[: args.limit]
    if args.model:
        config.primary_model = args.model
    if args.skip_er:
        config.run_expert_rating = False

    print(f"Running pilot with {len(config.personas)} profiles on {config.primary_model}")
    payload = asyncio.run(run_experiment(config))
    print("\n=== Effect Sizes (BFI high-vs-low per dim) ===")
    for dim, es in payload["effect_sizes"].items():
        if "cohens_d" in es:
            marker = "✓" if es["meets_threshold"] else "✗"
            print(
                f"  [{dim}] n={es['n_high']}+{es['n_low']}  "
                f"d={es['cohens_d']:+.2f}  g={es['hedges_g']:+.2f}  "
                f"CI95=[{es['ci_95_lo']:+.2f}, {es['ci_95_hi']:+.2f}]  {marker}"
            )
        else:
            print(f"  [{dim}] {es}")


if __name__ == "__main__":
    main()
