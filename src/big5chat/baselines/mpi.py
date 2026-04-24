"""MPI (Machine Personality Inventory) evaluator.

Implements the 120-item MPI methodology from Jiang et al., NeurIPS 2023.
Reads the inventory CSV shipped with the cloned MPI repo verbatim.

Persona induction: none by default (neutral baseline). MPI's P^2 prompting
can be toggled by passing a persona system prompt via `system_prompt_override`.

Template (verbatim from MPI paper):
    Question:
    Given a statement of you: "You {item_text}."
    Please choose from the following options ...
    (A) Very Accurate ... (E) Very Inaccurate

Scoring:
    A=5 B=4 C=3 D=2 E=1; if key == -1, score is reversed (6 - raw).
"""

from __future__ import annotations

import asyncio
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


MPI_TEMPLATE = """Question:
Given a statement of you: "You {text}."
Please choose from the following options to identify how accurately this statement describes you.
Options:
(A). Very Accurate
(B). Moderately Accurate
(C). Neither Accurate Nor Inaccurate
(D). Moderately Inaccurate
(E). Very Inaccurate

Answer:"""

SCORES_MPI = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}


@dataclass
class MPIItem:
    text: str
    label_ocean: str  # O|C|E|A|N
    key: int  # 1 or -1
    label_raw: str = ""


@dataclass
class MPIItemResponse:
    item_text: str
    dim: str
    raw_response: str
    choice: str | None
    score: int | None  # 1..5 after key-reverse
    key: int


@dataclass
class MPIResult:
    dim_mean: dict[str, float]  # O|C|E|A|N -> mean 1..5
    dim_std: dict[str, float]
    dim_n: dict[str, int]
    choice_counts: dict[str, int]
    raw: list[MPIItemResponse] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dim_mean": self.dim_mean,
            "dim_std": self.dim_std,
            "dim_n": self.dim_n,
            "choice_counts": self.choice_counts,
            "raw": [
                {
                    "item_text": r.item_text,
                    "dim": r.dim,
                    "raw_response": r.raw_response,
                    "choice": r.choice,
                    "score": r.score,
                    "key": r.key,
                }
                for r in self.raw
            ],
        }


def load_mpi_inventory(csv_path: Path | str) -> list[MPIItem]:
    """Load 120-item or 1k-item MPI CSV. Columns: label_raw, text, label_ocean, key."""
    items: list[MPIItem] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(
                MPIItem(
                    text=row["text"],
                    label_ocean=row["label_ocean"].strip().upper(),
                    key=int(row["key"]),
                    label_raw=row.get("label_raw", ""),
                )
            )
    return items


def _parse_mpi_choice(raw: str) -> str | None:
    match = re.search(r"(^|\W)([ABCDEabcde])(?:\W|$)", raw)
    if match:
        return match.group(2).upper()
    match = re.search(r"[ABCDEabcde]", raw)
    if match:
        return match.group(0).upper()
    return None


class MPIEvaluator:
    """MPI 120/1k-item evaluator compatible with big5chat providers.

    Args:
        provider: Any big5chat LLMProvider (OpenAI recommended).
        inventory_path: Path to MPI CSV. Defaults to
            `external/MPI/inventories/mpi_120.csv`.
        assembler: Optional PromptAssembler for applying big5chat personas
            as the system prompt (otherwise uses a neutral/blank system).
        system_prompt_override: Manual override for the system prompt,
            used to reproduce MPI's P^2 prompting.
    """

    def __init__(
        self,
        provider: LLMProvider,
        inventory_path: Path | str = "external/MPI/inventories/mpi_120.csv",
        assembler: PromptAssembler | None = None,
        system_prompt_override: str | None = None,
        max_concurrency: int = 10,
    ):
        self.provider = provider
        self.items = load_mpi_inventory(inventory_path)
        self.assembler = assembler
        self.system_prompt_override = system_prompt_override
        self.max_concurrency = max_concurrency

    async def evaluate(
        self,
        persona_spec: PersonaSpec | None = None,
        seed_base: int = 42,
    ) -> MPIResult:
        """Run all inventory items against the LLM and aggregate.

        Args:
            persona_spec: If provided and `assembler` is set, the persona's
                Serapio-Garcia system prompt is used. If neither this nor
                `system_prompt_override` is provided, runs the neutral baseline
                (empty system) which reproduces MPI's default setting.
        """
        if self.system_prompt_override is not None:
            system = self.system_prompt_override
        elif persona_spec is not None and self.assembler is not None:
            system = self.assembler.assemble(persona_spec)
        else:
            system = ""

        sem = asyncio.Semaphore(self.max_concurrency)
        tasks = [
            asyncio.create_task(self._score_item(sem, item, system, seed_base))
            for item in self.items
        ]
        responses: list[MPIItemResponse] = await asyncio.gather(*tasks)

        by_dim: dict[str, list[int]] = {"O": [], "C": [], "E": [], "A": [], "N": []}
        counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "UNK": 0}
        for r in responses:
            if r.choice is None:
                counts["UNK"] += 1
            else:
                counts[r.choice] = counts.get(r.choice, 0) + 1
            if r.score is not None:
                by_dim[r.dim].append(r.score)

        def _mean(xs): return sum(xs) / len(xs) if xs else float("nan")
        def _std(xs):
            if len(xs) < 2: return 0.0
            m = _mean(xs)
            return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5

        return MPIResult(
            dim_mean={d: _mean(xs) for d, xs in by_dim.items()},
            dim_std={d: _std(xs) for d, xs in by_dim.items()},
            dim_n={d: len(xs) for d, xs in by_dim.items()},
            choice_counts=counts,
            raw=responses,
        )

    async def _score_item(
        self,
        sem: asyncio.Semaphore,
        item: MPIItem,
        system_prompt: str,
        seed: int,
    ) -> MPIItemResponse:
        user_prompt = MPI_TEMPLATE.format(text=item.text.lower())
        async with sem:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            resp = await self.provider.complete(
                messages=messages,
                temperature=0.0,
                seed=seed if self.provider.supports_seed else None,
                max_tokens=8,
            )
        choice = _parse_mpi_choice(resp.content.strip())
        if choice is None:
            score = None
        else:
            raw_score = SCORES_MPI[choice]
            score = raw_score if item.key == 1 else 6 - raw_score
        return MPIItemResponse(
            item_text=item.text,
            dim=item.label_ocean,
            raw_response=resp.content,
            choice=choice,
            score=score,
            key=item.key,
        )
