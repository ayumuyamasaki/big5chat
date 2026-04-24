"""Output moderation via OpenAI Moderation API (ConstructionPlan §I.2)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ModerationResult:
    flagged: bool
    categories: dict[str, bool]
    scores: dict[str, float]


async def moderate_openai(text: str, api_key: str | None = None) -> ModerationResult:
    """Run OpenAI omni-moderation-latest on the given text."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    resp = await client.moderations.create(
        model="omni-moderation-latest",
        input=text,
    )
    r = resp.results[0]
    return ModerationResult(
        flagged=r.flagged,
        categories=dict(r.categories) if hasattr(r.categories, "keys") else r.categories.model_dump(),
        scores=dict(r.category_scores) if hasattr(r.category_scores, "keys") else r.category_scores.model_dump(),
    )
