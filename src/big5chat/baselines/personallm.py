"""PersonaLLM (Jiang et al. NAACL 2024) evaluator.

Implements the 44-item BFI methodology from the PersonaLLM paper.
Reads `external/PersonaLLM/prompts/bfi_prompt.txt` and `bfi_scores.txt` verbatim.

Persona induction: PersonaLLM's canonical method is a binary system prompt:
    "You are a character who is extroverted, agreeable, conscientious,
     emotionally stable, and open to experience."

Scoring: 1..5 Likert, with reversed items flipped (5 -> 1, 4 -> 2, etc.).
Scores are then summed within each of the 5 BFI factors.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


# PersonaLLM's 32 binary persona combinations (5 dimensions × 2 poles each)
PERSONALLM_POLES: dict[str, dict[int, str]] = {
    "E": {1: "extroverted", -1: "introverted"},
    "A": {1: "agreeable", -1: "antagonistic"},
    "C": {1: "conscientious", -1: "unconscientious"},
    "N": {1: "neurotic", -1: "emotionally stable"},
    "O": {1: "open to experience", -1: "closed to experience"},
}


# Mapping from long trait name in bfi_scores.txt to OCEAN letter
TRAIT_TO_DIM = {
    "Extraversion": "E",
    "Agreeableness": "A",
    "Conscientiousness": "C",
    "Neuroticism": "N",
    "Openness": "O",
}


@dataclass
class PersonaLLMItem:
    idx: int  # 0-based
    letter: str  # (a)..(rr) style
    question: str
    dim: str
    reverse: bool


@dataclass
class PersonaLLMResult:
    dim_sum: dict[str, float]  # summed scores per dim (PersonaLLM's primary output)
    dim_mean: dict[str, float]  # per-item mean per dim
    dim_n: dict[str, int]
    raw_response: str  # the full LLM answer string
    parsed_scores: list[int]  # per-item 1..5 scores (reverse-applied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dim_sum": self.dim_sum,
            "dim_mean": self.dim_mean,
            "dim_n": self.dim_n,
            "raw_response": self.raw_response,
            "parsed_scores": self.parsed_scores,
        }


def load_bfi_items(scores_path: Path | str) -> list[PersonaLLMItem]:
    """Load the 44-item BFI metadata (trait + reverse flags)."""
    lines = Path(scores_path).read_text(encoding="utf-8").splitlines()
    # Header: trait\treverse\tquestion
    items: list[PersonaLLMItem] = []
    # Letters: a-z, then aa-rr (up to 44)
    letters = [chr(ord("a") + i) for i in range(26)]
    letters += [f"{chr(ord('a') + i)}{chr(ord('a') + i)}" for i in range(18)]
    for idx, line in enumerate(lines[1:]):
        if not line.strip():
            continue
        trait, reverse, question = line.split("\t")
        items.append(
            PersonaLLMItem(
                idx=idx,
                letter=letters[idx] if idx < len(letters) else f"z{idx}",
                question=question.strip(),
                dim=TRAIT_TO_DIM[trait.strip()],
                reverse=(reverse.strip().upper() == "R"),
            )
        )
    return items


def load_bfi_prompt_template(prompt_path: Path | str) -> str:
    """Load the PersonaLLM BFI user prompt (with %PERSONA% placeholder)."""
    return Path(prompt_path).read_text(encoding="utf-8")


def build_persona_description(big5: Big5Values) -> str:
    """Convert Big5Values to PersonaLLM's comma-separated persona phrase.

    Rule: value >= 3 (1-5 scale, 3=neutral) -> high pole word, else -> low
    pole word. 3 defaults to high pole for simplicity (PersonaLLM itself is binary).
    """
    order = ["E", "A", "C", "N", "O"]
    words: list[str] = []
    for dim in order:
        v = getattr(big5, dim)
        pole = 1 if v >= 3 else -1
        words.append(PERSONALLM_POLES[dim][pole])
    words[-1] = "and " + words[-1]
    return ", ".join(words)


def _parse_bfi_response(raw: str, n_items: int = 44) -> list[int | None]:
    """Extract 44 Likert ratings from the LLM free-text response.

    Expected format from the paper's prompt: "(a) 5\n(b) 3\n(c) 4\n..."
    """
    scores: list[int | None] = [None] * n_items
    # Match "(a) <digit>" and "(aa) <digit>" patterns
    pattern = re.compile(r"\(([a-z]{1,2})\)\s*([1-5])", re.IGNORECASE)
    letters: list[str] = [chr(ord("a") + i) for i in range(26)]
    letters += [f"{chr(ord('a') + i)}{chr(ord('a') + i)}" for i in range(18)]
    letter_to_idx = {l: i for i, l in enumerate(letters)}
    for match in pattern.finditer(raw):
        letter = match.group(1).lower()
        score = int(match.group(2))
        if letter in letter_to_idx and letter_to_idx[letter] < n_items:
            scores[letter_to_idx[letter]] = score
    return scores


class PersonaLLMEvaluator:
    """PersonaLLM 44-item BFI evaluator.

    Note: PersonaLLM's methodology is one single LLM call that returns all 44
    Likert answers at once. Retry-on-parse-fail is applied (up to n_retries).
    """

    def __init__(
        self,
        provider: LLMProvider,
        prompt_path: Path | str = "external/PersonaLLM/prompts/bfi_prompt.txt",
        scores_path: Path | str = "external/PersonaLLM/prompts/bfi_scores.txt",
        n_retries: int = 3,
    ):
        self.provider = provider
        self.user_prompt_template = load_bfi_prompt_template(prompt_path)
        self.items = load_bfi_items(scores_path)
        self.n_retries = n_retries

    async def evaluate(
        self,
        persona_spec: PersonaSpec | None = None,
        persona_description: str | None = None,
        mode: Literal["personallm_native", "big5chat_persona"] = "personallm_native",
        assembler: PromptAssembler | None = None,
        seed_base: int = 42,
    ) -> PersonaLLMResult:
        """Run one BFI evaluation.

        Args:
            persona_spec: big5chat PersonaSpec (used to derive persona string
                under personallm_native, or the full system prompt under
                big5chat_persona mode).
            persona_description: Override the persona phrase. If provided, takes
                priority over persona_spec.
            mode:
                - "personallm_native": replicates the paper's prompt format
                  ("You are a chatbot who is ...") as the user prompt prefix.
                - "big5chat_persona": uses the Serapio-Garcia system prompt
                  from big5chat and appends the BFI items as the user message.
                  Use this for apples-to-apples comparison against big5chat.
            assembler: Required when mode == "big5chat_persona".
        """
        if persona_description is None and persona_spec is not None:
            persona_description = build_persona_description(persona_spec.big5_values)
        if persona_description is None:
            persona_description = "a character"  # neutral

        # Construct the user prompt (same for both modes; mode differs at system level)
        user_prompt = self.user_prompt_template.replace("%PERSONA%", persona_description)

        messages: list[dict[str, str]] = []
        if mode == "big5chat_persona":
            if persona_spec is None or assembler is None:
                raise ValueError("big5chat_persona mode requires persona_spec + assembler")
            system = assembler.assemble(persona_spec)
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user_prompt})

        raw = ""
        parsed: list[int | None] = []
        for attempt in range(self.n_retries):
            resp = await self.provider.complete(
                messages=messages,
                temperature=0.7,
                seed=(seed_base + attempt) if self.provider.supports_seed else None,
                max_tokens=800,
            )
            raw = resp.content
            parsed = _parse_bfi_response(raw, n_items=len(self.items))
            non_null = [s for s in parsed if s is not None]
            if len(non_null) >= len(self.items) * 0.9:  # at least 90% parsed
                break

        scores_with_reverse: list[int] = []
        by_dim_sum: dict[str, float] = {"O": 0.0, "C": 0.0, "E": 0.0, "A": 0.0, "N": 0.0}
        by_dim_vals: dict[str, list[int]] = {"O": [], "C": [], "E": [], "A": [], "N": []}
        for item, score in zip(self.items, parsed):
            if score is None:
                scores_with_reverse.append(-1)
                continue
            s = (6 - score) if item.reverse else score
            scores_with_reverse.append(s)
            by_dim_sum[item.dim] += s
            by_dim_vals[item.dim].append(s)

        def _mean(xs): return sum(xs) / len(xs) if xs else float("nan")

        return PersonaLLMResult(
            dim_sum=by_dim_sum,
            dim_mean={d: _mean(xs) for d, xs in by_dim_vals.items()},
            dim_n={d: len(xs) for d, xs in by_dim_vals.items()},
            raw_response=raw,
            parsed_scores=scores_with_reverse,
        )
