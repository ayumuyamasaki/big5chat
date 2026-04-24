"""TRAIT scenario MCQ evaluation (Layer 5c)."""

from __future__ import annotations

import asyncio
import json
import math
import random
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


@dataclass
class TraitScenario:
    id: str
    dim: str
    situation: str
    question: str
    options: dict[str, str]


@dataclass
class TraitScenarioResult:
    scenario_id: str
    dim: str
    h_probability: float
    chosen_pole: str | None
    ordering: str
    raw_response: str
    logprobs_used: bool


@dataclass
class TraitResult:
    dim_scores: dict[str, float]
    per_scenario: list[TraitScenarioResult] = field(default_factory=list)

    def dim_scores_5point(self) -> dict[str, float]:
        return {d: 1.0 + 4.0 * p for d, p in self.dim_scores.items()}


def _load_scenarios(language: str = "ja") -> list[TraitScenario]:
    fname = f"trait_scenarios_{language}.json"
    with resources.files("big5chat.evaluation.items").joinpath(fname).open(
        "r", encoding="utf-8"
    ) as f:
        data = json.load(f)
    return [
        TraitScenario(
            id=s["id"],
            dim=s["dim"],
            situation=s["situation"],
            question=s["question"],
            options=s["options"],
        )
        for s in data["scenarios"]
    ]


# --- Language-specific MCQ framing ---

_MCQ_LABELS = {
    "ja": {
        "situation": "状況：",
        "softener_prefix": "どちらかといえば、",
        "instruction": "最も自分に当てはまる選択肢をアルファベット1文字で答えてください。",
    },
    "zh": {
        "situation": "情境：",
        "softener_prefix": "相对来说，",
        "instruction": "请用一个字母回答最符合你自己的选项。",
    },
    "en": {
        "situation": "Situation: ",
        "softener_prefix": "Somewhat, ",
        "instruction": "Answer with a single letter indicating the option that best describes you.",
    },
}


def _format_mcq(
    scenario: TraitScenario, order: list[str], rng: random.Random, language: str = "ja"
) -> tuple[str, dict[str, str]]:
    labels = _MCQ_LABELS.get(language, _MCQ_LABELS["ja"])
    items = [
        ("H", scenario.options["H"]),
        ("H", f"{labels['softener_prefix']}{scenario.options['H']}"),
        ("L", scenario.options["L"]),
        ("L", f"{labels['softener_prefix']}{scenario.options['L']}"),
    ]
    h_items = [i for i in items if i[0] == "H"]
    l_items = [i for i in items if i[0] == "L"]
    rng.shuffle(h_items)
    rng.shuffle(l_items)
    h_iter = iter(h_items)
    l_iter = iter(l_items)
    arranged = [next(h_iter) if p == "H" else next(l_iter) for p in order]

    letters = ["A", "B", "C", "D"]
    letter_to_pole: dict[str, str] = {}
    lines = [f"{labels['situation']}{scenario.situation}", scenario.question]
    for letter, (pole, text) in zip(letters, arranged):
        lines.append(f"{letter}. {text}")
        letter_to_pole[letter] = pole
    lines.append(labels["instruction"])
    return "\n".join(lines), letter_to_pole


def _extract_option(response: str) -> str | None:
    match = re.search(r"\b([ABCD])\b", response)
    if match:
        return match.group(1)
    match = re.search(r"[ABCDa-d]", response)
    if match:
        return match.group(0).upper() if match.group(0).isalpha() else None
    return None


def _h_prob_from_logprobs(
    top_logprobs: dict[str, float], letter_to_pole: dict[str, str]
) -> float | None:
    probs = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
    any_hit = False
    for tok, lp in top_logprobs.items():
        letter = tok.strip().upper()
        if letter in probs:
            probs[letter] += math.exp(lp)
            any_hit = True
    if not any_hit:
        return None
    total = sum(probs.values())
    if total <= 0:
        return None
    norm = {k: v / total for k, v in probs.items()}
    h_mass = sum(norm[l] for l, pole in letter_to_pole.items() if pole == "H")
    return h_mass


class TraitMCQEvaluator:
    def __init__(
        self,
        provider: LLMProvider,
        assembler: PromptAssembler | None = None,
        orderings: list[list[str]] | None = None,
        max_concurrency: int = 10,
        shuffle_seed: int = 42,
    ):
        self.provider = provider
        self.assembler = assembler or PromptAssembler()
        self.orderings = orderings or [["H", "L", "H", "L"], ["L", "H", "L", "H"]]
        self.max_concurrency = max_concurrency
        self.shuffle_seed = shuffle_seed

    async def evaluate(self, persona_spec: PersonaSpec, seed_base: int = 42) -> TraitResult:
        scenarios = _load_scenarios(persona_spec.language)
        system_prompt = self.assembler.assemble(persona_spec)
        sem = asyncio.Semaphore(self.max_concurrency)

        tasks = []
        for scen in scenarios:
            for o_idx, ordering in enumerate(self.orderings):
                tasks.append(
                    asyncio.create_task(
                        self._score_scenario(
                            sem, system_prompt, scen, ordering, o_idx,
                            seed_base + o_idx, persona_spec.language,
                        )
                    )
                )
        per_scenario: list[TraitScenarioResult] = await asyncio.gather(*tasks)

        by_dim: dict[str, list[float]] = {"O": [], "C": [], "E": [], "A": [], "N": []}
        for r in per_scenario:
            by_dim[r.dim].append(r.h_probability)
        dim_scores = {
            d: (sum(xs) / len(xs) if xs else float("nan")) for d, xs in by_dim.items()
        }
        return TraitResult(dim_scores=dim_scores, per_scenario=per_scenario)

    async def _score_scenario(
        self, sem, system_prompt, scen, ordering, o_idx, seed, language
    ) -> TraitScenarioResult:
        rng = random.Random(self.shuffle_seed + hash(scen.id) % 1000 + o_idx)
        prompt_text, letter_to_pole = _format_mcq(scen, ordering, rng, language)
        async with sem:
            use_lp = self.provider.supports_logprobs
            resp = await self.provider.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.0,
                seed=seed if self.provider.supports_seed else None,
                max_tokens=2,
                logprobs=use_lp,
                top_logprobs=5 if use_lp else 0,
            )
        h_prob: float | None = None
        if use_lp and resp.logprobs:
            first = resp.logprobs[0]
            all_lps = {first.token: first.logprob, **first.top_logprobs}
            h_prob = _h_prob_from_logprobs(all_lps, letter_to_pole)

        chosen_letter = _extract_option(resp.content.strip())
        chosen_pole = letter_to_pole.get(chosen_letter) if chosen_letter else None
        if h_prob is None:
            h_prob = 1.0 if chosen_pole == "H" else (0.0 if chosen_pole == "L" else 0.5)

        return TraitScenarioResult(
            scenario_id=scen.id,
            dim=scen.dim,
            h_probability=h_prob,
            chosen_pole=chosen_pole,
            ordering="".join(ordering),
            raw_response=resp.content,
            logprobs_used=use_lp and bool(resp.logprobs),
        )
