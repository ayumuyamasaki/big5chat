"""Self-report BFI evaluation (Layer 5a).

Runs the BFI inventory against a persona-instantiated LLM, aggregating across
3 prompt variants x 2 postamble orderings x n repetitions.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler
from big5chat.prompts.postambles import (
    POSTAMBLE_RESPONSE_TOKENS,
    postamble,
    postamble_scale_max,
)


@dataclass
class BFIItem:
    id: str
    text: str
    dim: str
    reversed: bool
    facet: str | None = None


@dataclass
class BFIItemResponse:
    item_id: str
    dim: str
    raw_response: str
    parsed_score: float | None
    reversed_applied_score: float | None
    postamble_id: int
    variant: str
    rep: int


@dataclass
class BFIResult:
    dim_scores: dict[str, float]
    dim_std: dict[str, float]
    dim_n: dict[str, int]
    raw: list[BFIItemResponse] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dim_scores": self.dim_scores,
            "dim_std": self.dim_std,
            "dim_n": self.dim_n,
            "raw": [
                {
                    "item_id": r.item_id,
                    "dim": r.dim,
                    "raw_response": r.raw_response,
                    "parsed_score": r.parsed_score,
                    "reversed_applied_score": r.reversed_applied_score,
                    "postamble_id": r.postamble_id,
                    "variant": r.variant,
                    "rep": r.rep,
                }
                for r in self.raw
            ],
        }


def _load_items(language: str, items_path: Path | None = None) -> list[BFIItem]:
    if items_path is None:
        fname = f"bfi2_{language}.json"
        with resources.files("big5chat.evaluation.items").joinpath(fname).open(
            "r", encoding="utf-8"
        ) as f:
            data = json.load(f)
    else:
        with open(items_path, encoding="utf-8") as f:
            data = json.load(f)
    return [
        BFIItem(
            id=it["id"],
            text=it["text"],
            dim=it["dim"],
            reversed=it.get("reversed", False),
            facet=it.get("facet"),
        )
        for it in data["items"]
    ]


def _parse_response(raw: str, postamble_id: int) -> int | None:
    tokens = POSTAMBLE_RESPONSE_TOKENS[postamble_id]
    for tok, val in tokens.items():
        if re.search(rf"(^|\W){re.escape(tok)}(\W|$)", raw):
            return val
    match = re.search(r"[A-Ea-e1-7]", raw)
    if match:
        return tokens.get(match.group(0))
    return None


def _normalize_to_5(score: int | None, postamble_id: int) -> float | None:
    if score is None:
        return None
    scale_max = postamble_scale_max(postamble_id)
    if scale_max == 5:
        return float(score)
    return 1.0 + (score - 1) * (4.0 / (scale_max - 1))


def _format_user_prompt(item_text: str, pb: str, language: str) -> str:
    if language == "zh":
        return f"关于以下陈述，{pb}\n\n陈述：{item_text}"
    if language == "ja":
        return f"次の記述について、{pb}\n\n記述：{item_text}"
    return f"Statement: {item_text}\n\n{pb}"


class BFIEvaluator:
    """Runs BFI against an LLM-instantiated persona."""

    def __init__(
        self,
        provider: LLMProvider,
        assembler: PromptAssembler | None = None,
        postambles: list[int] | None = None,
        variants: list[str] | None = None,
        n_reps: int = 1,
        max_concurrency: int = 10,
        items_path: Path | None = None,
    ):
        self.provider = provider
        self.assembler = assembler or PromptAssembler()
        self.postambles = postambles if postambles is not None else [0, 1]
        self.variants = variants if variants is not None else ["A", "B", "C"]
        self.n_reps = n_reps
        self.max_concurrency = max_concurrency
        self.items_path = items_path

    async def evaluate(
        self,
        persona_spec: PersonaSpec,
        seed_base: int = 42,
    ) -> BFIResult:
        items = _load_items(persona_spec.language, self.items_path)
        sem = asyncio.Semaphore(self.max_concurrency)

        tasks: list[asyncio.Task] = []
        for rep in range(self.n_reps):
            for pid in self.postambles:
                for v in self.variants:
                    spec = persona_spec.with_updates(
                        item_postamble_id=pid, prompt_variant=v
                    )
                    for item in items:
                        tasks.append(
                            asyncio.create_task(
                                self._score_item(
                                    sem, spec, item, pid, v, rep, seed_base + rep
                                )
                            )
                        )

        responses: list[BFIItemResponse] = await asyncio.gather(*tasks)
        by_dim: dict[str, list[float]] = {"O": [], "C": [], "E": [], "A": [], "N": []}
        for r in responses:
            if r.reversed_applied_score is not None:
                by_dim[r.dim].append(r.reversed_applied_score)

        def _mean(xs): return sum(xs) / len(xs) if xs else float("nan")
        def _std(xs):
            if len(xs) < 2: return 0.0
            m = _mean(xs)
            return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5

        return BFIResult(
            dim_scores={d: _mean(xs) for d, xs in by_dim.items()},
            dim_std={d: _std(xs) for d, xs in by_dim.items()},
            dim_n={d: len(xs) for d, xs in by_dim.items()},
            raw=responses,
        )

    async def _score_item(
        self, sem, spec, item, postamble_id, variant, rep, seed
    ) -> BFIItemResponse:
        async with sem:
            system = self.assembler.assemble(spec)
            pb = postamble(spec.language, postamble_id)
            user_text = _format_user_prompt(item.text, pb, spec.language)
            response = await self.provider.complete(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.0,
                seed=seed if self.provider.supports_seed else None,
                max_tokens=4,
                logprobs=False,
            )
            raw_score = _parse_response(response.content.strip(), postamble_id)
            normalized = _normalize_to_5(raw_score, postamble_id)
            reversed_score: float | None = None
            if normalized is not None:
                reversed_score = 6.0 - normalized if item.reversed else normalized
            return BFIItemResponse(
                item_id=item.id,
                dim=item.dim,
                raw_response=response.content,
                parsed_score=normalized,
                reversed_applied_score=reversed_score,
                postamble_id=postamble_id,
                variant=variant,
                rep=rep,
            )
