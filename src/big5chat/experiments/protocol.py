"""Phase-0 pilot protocol runner."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from big5chat.analysis.effect_size import effect_size_report
from big5chat.dialogue.providers import get_provider
from big5chat.evaluation.bfi import BFIEvaluator, BFIResult
from big5chat.evaluation.expert_rating import ERResult, ExpertRatingEvaluator
from big5chat.evaluation.trait_mcq import TraitMCQEvaluator, TraitResult
from big5chat.experiments.config import ExperimentConfig, PersonaConfig
from big5chat.journal import JsonlJournal
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


@dataclass
class ProfileReport:
    profile_id: str
    persona_hash: str
    bfi: dict[str, Any] | None = None
    expert_rating: dict[str, Any] | None = None
    trait_mcq: dict[str, Any] | None = None


async def run_experiment(config: ExperimentConfig) -> dict[str, Any]:
    """Run the full evaluation pipeline across all configured personas."""
    primary = get_provider(config.primary_model)
    judges = [get_provider(m) for m in config.judge_models]
    assembler = PromptAssembler()

    bfi_eval = (
        BFIEvaluator(
            primary,
            assembler,
            n_reps=config.n_reps,
            max_concurrency=config.max_concurrency,
            items_filename=config.bfi_items_filename,
        )
        if config.run_bfi
        else None
    )
    er_eval = (
        ExpertRatingEvaluator(
            primary, judges, assembler, max_concurrency=config.max_concurrency
        )
        if config.run_expert_rating
        else None
    )
    trait_eval = (
        TraitMCQEvaluator(
            primary, assembler, max_concurrency=config.max_concurrency
        )
        if config.run_trait_mcq
        else None
    )

    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    journal_path = log_dir / f"{config.experiment_id}.jsonl"

    reports: list[ProfileReport] = []
    with JsonlJournal(journal_path, experiment_id=config.experiment_id) as journal:
        journal.log_event("experiment_start", {"config": config.model_dump()})

        for pconf in config.personas:
            spec = pconf.to_persona_spec()
            report = ProfileReport(
                profile_id=spec.profile_id,
                persona_hash=spec.profile_hash(),
            )

            # BFI
            if bfi_eval is not None:
                bfi_result: BFIResult = await bfi_eval.evaluate(
                    spec, seed_base=config.seed_base
                )
                report.bfi = bfi_result.to_dict()
                journal.log_event(
                    "bfi_completed",
                    {
                        "profile_id": spec.profile_id,
                        "dim_scores": bfi_result.dim_scores,
                    },
                )

            # Expert Rating
            if er_eval is not None:
                er_result: ERResult = await er_eval.evaluate(
                    spec, seed_base=config.seed_base
                )
                report.expert_rating = {
                    "dim_scores": er_result.dim_scores,
                    "n_judges": len(config.judge_models),
                    "n_questions": len(er_result.qa_pairs),
                }
                journal.log_event(
                    "er_completed",
                    {
                        "profile_id": spec.profile_id,
                        "dim_scores": er_result.dim_scores,
                    },
                )

            # TRAIT MCQ
            if trait_eval is not None:
                trait_result: TraitResult = await trait_eval.evaluate(
                    spec, seed_base=config.seed_base
                )
                report.trait_mcq = {
                    "dim_scores_01": trait_result.dim_scores,
                    "dim_scores_5pt": trait_result.dim_scores_5point(),
                    "n_scenarios": len(trait_result.per_scenario),
                }
                journal.log_event(
                    "trait_completed",
                    {
                        "profile_id": spec.profile_id,
                        "dim_scores": trait_result.dim_scores,
                    },
                )

            reports.append(report)

        journal.log_event("experiment_end", {"n_profiles": len(reports)})

    # Cross-profile effect-size analysis
    effect_sizes = _compute_effect_sizes(config.personas, reports)

    # Write results JSON
    out_dir = Path(config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"{config.experiment_id}_results.json"
    payload = {
        "experiment_id": config.experiment_id,
        "config": config.model_dump(),
        "profile_reports": [
            {
                "profile_id": r.profile_id,
                "persona_hash": r.persona_hash,
                "bfi": r.bfi,
                "expert_rating": r.expert_rating,
                "trait_mcq": r.trait_mcq,
            }
            for r in reports
        ],
        "effect_sizes": effect_sizes,
    }
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _compute_effect_sizes(
    personas: list[PersonaConfig], reports: list[ProfileReport]
) -> dict[str, dict[str, Any]]:
    """For each Big5 dim, compare profiles with high vs low value on that dim.

    Uses BFI dim_scores as the primary outcome. A profile is 'high' on dim X
    if its big5_values.X > 3 (1-5 scale, 3 = neutral), 'low' if < 3.
    """
    from big5chat.analysis.effect_size import effect_size_report as _esr

    result: dict[str, dict[str, Any]] = {}
    for dim in ["O", "C", "E", "A", "N"]:
        high_scores: list[float] = []
        low_scores: list[float] = []
        for pconf, rep in zip(personas, reports):
            if rep.bfi is None:
                continue
            score = rep.bfi["dim_scores"].get(dim)
            if score is None:
                continue
            val = getattr(pconf.big5_values, dim)
            if val > 3:
                high_scores.append(score)
            elif val < 3:
                low_scores.append(score)
        if len(high_scores) >= 2 and len(low_scores) >= 2:
            result[dim] = _esr(high_scores, low_scores)
        else:
            result[dim] = {"error": "insufficient data"}
    return result
