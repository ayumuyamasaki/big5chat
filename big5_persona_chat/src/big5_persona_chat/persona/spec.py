"""PersonaSpec: Big5 ペルソナの正規データモデル。

EN / JA / ZH の 3 言語に対応。

ConstructionPlan.md §D.6 "完全な実装JSON (再現可能仕様)" 由来。
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Big5Dim = Literal["O", "C", "E", "A", "N"]
Language = Literal["en", "ja", "zh"]


class Big5Values(BaseModel):
    """Big5 プロファイル(Likert -4 〜 +4 の 9 段階)。"""

    model_config = ConfigDict(frozen=True)

    O: int = Field(ge=-4, le=4, description="Openness (開放性)")
    C: int = Field(ge=-4, le=4, description="Conscientiousness (誠実性)")
    E: int = Field(ge=-4, le=4, description="Extraversion (外向性)")
    A: int = Field(ge=-4, le=4, description="Agreeableness (協調性)")
    N: int = Field(ge=-4, le=4, description="Neuroticism (神経症傾向)")

    def as_dict(self) -> dict[str, int]:
        return {"O": self.O, "C": self.C, "E": self.E, "A": self.A, "N": self.N}


class StyleParams(BaseModel):
    """ペルソナの文体パラメータ。

    フィールド値は言語依存の自由形式文字列(JA/ZH/EN いずれにもフィットさせるため
    厳密な Literal にしていない)。バリデーションは呼び出し側の責任。

    各言語での値の例:
        first_person:
            - ja: 私 / 僕 / 俺 / わたし / 自分 / あたし
            - zh: 我 / 本人 / 咱 / 人家 / 老子
            - en: I (基本的に一択)
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
    """完全なペルソナ仕様。

    マーカー/経歴データベースと組み合わせれば、1 つの PersonaSpec から
    システムプロンプトが一意に決定される。
    """

    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(
        description="人が読めるID。例: 'HELHN_LOXC_01'。自由形式。",
    )
    big5_values: Big5Values
    biographic_description_id: int = Field(
        ge=0, description="BIOGRAPHIES_{EN|JA|ZH} へのインデックス。"
    )
    item_postamble_id: int = Field(
        default=0, ge=0, le=4, description="(BFI 評価専用、本パッケージでは未使用) 互換目的で残す。"
    )
    prompt_variant: Literal["A", "B", "C"] = "A"
    language: Language = "ja"
    style: StyleParams | None = None

    n_markers_per_dim: int = Field(default=5, ge=1, le=8)

    @model_validator(mode="after")
    def _apply_default_style(self) -> PersonaSpec:
        if self.language in ("ja", "zh") and self.style is None:
            object.__setattr__(
                self, "style", _default_style_for(self.big5_values, self.language)
            )
        return self

    def profile_hash(self) -> str:
        """ログ/再現性監査用の短い安定ハッシュ(sha256 の先頭 16 文字)。"""
        blob = json.dumps(self.model_dump(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def with_updates(self, **fields) -> PersonaSpec:
        """指定フィールドだけ差し替えたコピーを返す。"""
        return self.model_copy(update=fields)


def _default_style_for(big5: Big5Values, language: Language = "ja") -> StyleParams:
    """Big5 から文体を推論するヒューリスティック。言語依存。"""
    if language == "zh":
        return _default_style_zh(big5)
    return _default_style_ja(big5)


def _default_style_ja(big5: Big5Values) -> StyleParams:
    if big5.E >= 2 and big5.A <= 0:
        first_person = "俺"
    elif big5.E >= 2:
        first_person = "僕"
    else:
        first_person = "私"

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
    """中国語(簡体字)の文体既定値。

    - 我 はほぼ普遍的なデフォルト。咱 (北方の口語) は高E+低A 向け。
    - 书面/口语/混合/随意 から選択。
    - 助詞頻度は 啊/吧/呢/嘛/哦 等の使用頻度を表す。
    """
    if big5.E >= 3 and big5.A <= -1:
        first_person = "咱"
    else:
        first_person = "我"

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
