"""PersonaSpec: the canonical Big5 persona data model.

Corresponds to ConstructionPlan.md §D.6 "完全な実装JSON (再現可能仕様)".
Supports three languages: Japanese (ja), English (en), Simplified Chinese (zh).
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Big5Dim = Literal["O", "C", "E", "A", "N"]
Language = Literal["en", "ja", "zh"]


class Big5Values(BaseModel):
    """Big5 profile on Likert -4 to +4 scale (9 levels)."""

    model_config = ConfigDict(frozen=True)

    O: int = Field(ge=-4, le=4, description="Openness")
    C: int = Field(ge=-4, le=4, description="Conscientiousness")
    E: int = Field(ge=-4, le=4, description="Extraversion")
    A: int = Field(ge=-4, le=4, description="Agreeableness")
    N: int = Field(ge=-4, le=4, description="Neuroticism")

    def as_dict(self) -> dict[str, int]:
        return {"O": self.O, "C": self.C, "E": self.E, "A": self.A, "N": self.N}


class StyleParams(BaseModel):
    """Stylistic parameters for the persona.

    Field values are language-dependent strings (free-form) rather than
    strict Literals so that Japanese / Chinese / English conventions can
    all fit the same schema. Validation is the caller's responsibility.

    Examples of valid values per language:
        first_person:
            - ja: 私 / 僕 / 俺 / わたし / 自分 / あたし
            - zh: 我 / 本人 / 咱 / 人家 / 老子
            - en: I (only one natural choice)
        sentence_ending:
            - ja: 敬体 / 常体 / 混合 / カジュアル
            - zh: 书面 / 口语 / 混合 / 随意
            - en: formal / casual / mixed
    """

    model_config = ConfigDict(frozen=True)

    first_person: str = "私"
    sentence_ending: str = "敬体"
    particle_frequency: Literal["低", "中", "高"] = "中"
    punctuation: Literal["標準", "多", "少"] = "標準"
    emoji: Literal["無", "少", "多"] = "無"
    onomatopoeia: Literal["無", "少", "多"] = "無"


class PersonaSpec(BaseModel):
    """Complete persona specification.

    One PersonaSpec fully determines a system prompt when combined with the
    shared marker/biography databases. The `profile_hash()` uniquely identifies
    the spec for logging / reproducibility audits.
    """

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(
        description="Human-readable ID, e.g. 'HELHN_LOXC_01'. Free-form.",
    )
    big5_values: Big5Values
    biographic_description_id: int = Field(
        ge=0, description="Index into BIOGRAPHIES_{EN|JA|ZH}."
    )
    item_postamble_id: int = Field(
        ge=0, le=4, description="Index into POSTAMBLES_{EN|JA|ZH} (5 variants)."
    )
    prompt_variant: Literal["A", "B", "C"] = "A"
    language: Language = "ja"
    style: StyleParams | None = None

    # Optional: override marker count (default 5 per Serapio-Garcia).
    n_markers_per_dim: int = Field(default=5, ge=1, le=8)

    @model_validator(mode="after")
    def _apply_default_style(self) -> PersonaSpec:
        if self.language in ("ja", "zh") and self.style is None:
            object.__setattr__(
                self, "style", _default_style_for(self.big5_values, self.language)
            )
        return self

    def profile_hash(self) -> str:
        """Stable short hash for JSONL logging (first 16 hex chars of sha256)."""
        blob = json.dumps(self.model_dump(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def with_updates(self, **fields) -> PersonaSpec:
        """Return a copy with given fields replaced."""
        return self.model_copy(update=fields)


def _default_style_for(big5: Big5Values, language: Language = "ja") -> StyleParams:
    """Heuristic style from Big5, language-aware.

    These defaults aim for ecological plausibility. Researchers should override
    explicitly when needed.
    """
    if language == "zh":
        return _default_style_zh(big5)
    return _default_style_ja(big5)


def _default_style_ja(big5: Big5Values) -> StyleParams:
    # First person
    if big5.E >= 2 and big5.A <= 0:
        first_person = "俺"
    elif big5.E >= 2:
        first_person = "僕"
    else:
        first_person = "私"

    # Sentence ending
    if big5.E >= 2 and big5.A >= 1:
        sentence_ending = "混合"
    elif big5.A <= -2:
        sentence_ending = "常体"
    elif big5.E >= 3 and big5.A <= 0:
        sentence_ending = "カジュアル"
    else:
        sentence_ending = "敬体"

    particle_frequency: Literal["低", "中", "高"] = (
        "高" if big5.E >= 2 else "低" if big5.E <= -2 else "中"
    )
    emoji: Literal["無", "少", "多"] = "少" if big5.E >= 2 and big5.A >= 1 else "無"
    onomatopoeia: Literal["無", "少", "多"] = "少" if big5.O >= 2 and big5.E >= 2 else "無"

    return StyleParams(
        first_person=first_person,
        sentence_ending=sentence_ending,
        particle_frequency=particle_frequency,
        emoji=emoji,
        onomatopoeia=onomatopoeia,
    )


def _default_style_zh(big5: Big5Values) -> StyleParams:
    """Chinese stylistic defaults (Simplified Mandarin conventions).

    - 我 is the near-universal default; 咱 (Northern colloquial) for high-E+low-A.
    - 书面 (formal written), 口语 (colloquial), 混合 (mixed), 随意 (casual).
    - Particle frequency tracks use of 啊/吧/呢/嘛/哦 etc.
    """
    # First person
    if big5.E >= 3 and big5.A <= -1:
        first_person = "咱"
    else:
        first_person = "我"

    # Sentence ending style
    if big5.E >= 2 and big5.A >= 1:
        sentence_ending = "混合"
    elif big5.A <= -2:
        sentence_ending = "书面"
    elif big5.E >= 3 and big5.A <= 0:
        sentence_ending = "随意"
    else:
        sentence_ending = "口语"

    particle_frequency: Literal["低", "中", "高"] = (
        "高" if big5.E >= 2 else "低" if big5.E <= -2 else "中"
    )
    emoji: Literal["無", "少", "多"] = "少" if big5.E >= 2 and big5.A >= 1 else "無"
    onomatopoeia: Literal["無", "少", "多"] = "少" if big5.O >= 2 and big5.E >= 2 else "無"

    return StyleParams(
        first_person=first_person,
        sentence_ending=sentence_ending,
        particle_frequency=particle_frequency,
        emoji=emoji,
        onomatopoeia=onomatopoeia,
    )
