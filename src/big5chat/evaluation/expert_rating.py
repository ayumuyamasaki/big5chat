"""Expert Rating evaluation (Layer 5b, InCharacter 2024 style)."""

from __future__ import annotations

import asyncio
import json
import re
import statistics
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from big5chat.dialogue.providers.base import LLMProvider
from big5chat.persona.spec import PersonaSpec
from big5chat.prompts.assembler import PromptAssembler


@dataclass
class InterviewQA:
    q_id: str
    question: str
    answer: str
    primary_dim: str


@dataclass
class ERResult:
    dim_scores: dict[str, float]
    justifications: dict[str, str]
    judge_raw: list[dict[str, Any]] = field(default_factory=list)
    qa_pairs: list[InterviewQA] = field(default_factory=list)


JUDGE_SYSTEM_JA = """あなたは性格心理学の専門家です。
以下はある人物（被面接者）へのインタビュー回答です。
回答内容のみから、Big5の各次元について1〜5のスコアを判定してください。
- 1 = 明らかに低い極（例: Extraversionなら非常に内向的）
- 3 = 中立
- 5 = 明らかに高い極（例: Extraversionなら非常に外向的）

必ず以下のJSONで返してください（コードフェンス不要）：
{
  "O": {"score": <int 1-5>, "justification": "..."},
  "C": {"score": <int 1-5>, "justification": "..."},
  "E": {"score": <int 1-5>, "justification": "..."},
  "A": {"score": <int 1-5>, "justification": "..."},
  "N": {"score": <int 1-5>, "justification": "..."}
}"""

JUDGE_SYSTEM_EN = """You are an expert in personality psychology.
The following is an interview with a person. Based only on the interview
content, rate each Big5 dimension on a 1-5 scale.
- 1 = clearly low pole (e.g., very introverted for Extraversion)
- 3 = neutral
- 5 = clearly high pole (e.g., very extraverted for Extraversion)

Always reply with JSON in this exact format (no code fences):
{
  "O": {"score": <int 1-5>, "justification": "..."},
  "C": {"score": <int 1-5>, "justification": "..."},
  "E": {"score": <int 1-5>, "justification": "..."},
  "A": {"score": <int 1-5>, "justification": "..."},
  "N": {"score": <int 1-5>, "justification": "..."}
}"""

JUDGE_SYSTEM_ZH = """你是一名性格心理学专家。
以下是对某个人（被访者）的访谈回答。
仅根据回答内容，请在1至5的量表上对Big5的每一个维度进行评分。
- 1 = 明显偏向低极（例如Extraversion上非常内向）
- 3 = 中立
- 5 = 明显偏向高极（例如Extraversion上非常外向）

请严格按照以下JSON格式作答（不要使用代码块标记）：
{
  "O": {"score": <int 1-5>, "justification": "..."},
  "C": {"score": <int 1-5>, "justification": "..."},
  "E": {"score": <int 1-5>, "justification": "..."},
  "A": {"score": <int 1-5>, "justification": "..."},
  "N": {"score": <int 1-5>, "justification": "..."}
}"""


def _judge_system(language: str) -> str:
    if language == "zh": return JUDGE_SYSTEM_ZH
    if language == "ja": return JUDGE_SYSTEM_JA
    return JUDGE_SYSTEM_EN


def _load_questions(language: str = "ja") -> list[dict[str, Any]]:
    fname = f"interview_qs_{language}.json"
    with resources.files("big5chat.evaluation.items").joinpath(fname).open(
        "r", encoding="utf-8"
    ) as f:
        data = json.load(f)
    return data["questions"]


def _parse_judge_json(raw: str) -> dict[str, Any]:
    stripped = re.sub(r"^```[a-zA-Z]*\s*|```\s*$", "", raw.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        stripped = match.group(0)
    return json.loads(stripped)


def _transcript_header(language: str) -> str:
    if language == "zh": return "【访谈全文】\n"
    if language == "ja": return "【インタビュー全文】\n"
    return "[FULL INTERVIEW]\n"


class ExpertRatingEvaluator:
    """Runs InCharacter-style expert rating."""

    def __init__(
        self,
        rpa_provider: LLMProvider,
        judge_providers: list[LLMProvider],
        assembler: PromptAssembler | None = None,
        max_concurrency: int = 10,
    ):
        if not judge_providers:
            raise ValueError("At least one judge provider is required")
        self.rpa_provider = rpa_provider
        self.judge_providers = judge_providers
        self.assembler = assembler or PromptAssembler()
        self.max_concurrency = max_concurrency

    async def evaluate(self, persona_spec: PersonaSpec, seed_base: int = 42) -> ERResult:
        questions = _load_questions(persona_spec.language)
        system_prompt = self.assembler.assemble(persona_spec)

        sem = asyncio.Semaphore(self.max_concurrency)
        qa_tasks = [
            asyncio.create_task(self._ask_question(sem, system_prompt, q, seed_base))
            for q in questions
        ]
        qa_pairs: list[InterviewQA] = await asyncio.gather(*qa_tasks)

        judge_tasks = [
            self._run_judge(jp, qa_pairs, seed_base, persona_spec.language)
            for jp in self.judge_providers
        ]
        judge_results = await asyncio.gather(*judge_tasks)

        consensus: dict[str, float] = {}
        justifications: dict[str, str] = {}
        for dim in ["O", "C", "E", "A", "N"]:
            scores = []
            justs = []
            for jr in judge_results:
                if dim in jr and "score" in jr[dim]:
                    scores.append(float(jr[dim]["score"]))
                    justs.append(jr[dim].get("justification", ""))
            consensus[dim] = statistics.median(scores) if scores else float("nan")
            justifications[dim] = " | ".join(justs)

        return ERResult(
            dim_scores=consensus,
            justifications=justifications,
            judge_raw=judge_results,
            qa_pairs=qa_pairs,
        )

    async def _ask_question(self, sem, system_prompt, question, seed) -> InterviewQA:
        async with sem:
            resp = await self.rpa_provider.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question["text"]},
                ],
                temperature=0.7,
                seed=seed if self.rpa_provider.supports_seed else None,
                max_tokens=400,
            )
            return InterviewQA(
                q_id=question["id"],
                question=question["text"],
                answer=resp.content,
                primary_dim=question["primary_dim"],
            )

    async def _run_judge(
        self, judge, qa_pairs, seed, language: str
    ) -> dict[str, Any]:
        transcript = "\n\n".join(f"Q: {qa.question}\nA: {qa.answer}" for qa in qa_pairs)
        header = _transcript_header(language)
        resp = await judge.complete(
            messages=[
                {"role": "system", "content": _judge_system(language)},
                {"role": "user", "content": f"{header}{transcript}"},
            ],
            temperature=0.0,
            seed=seed if judge.supports_seed else None,
            max_tokens=800,
        )
        try:
            return _parse_judge_json(resp.content)
        except (json.JSONDecodeError, ValueError):
            return {
                dim: {"score": 3, "justification": "PARSE_ERROR"}
                for dim in ["O", "C", "E", "A", "N"]
            }
