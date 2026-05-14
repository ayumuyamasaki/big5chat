"""ユーザー向けの薄い Persona ラッパ。

PersonaSpec が研究目的の完全仕様であるのに対し、Persona はゲーム等の
利用側で「最低限の意味」だけを露出するためのビュー。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from big5_persona_chat.persona.spec import Big5Values, PersonaSpec, StyleParams


class Persona(BaseModel):
    """ゲーム等から渡す軽量ペルソナ仕様。

    language はあえてこのクラスに持たせない: 同一の人格を複数言語で
    使い回せるよう、chat() 等の呼び出し時に渡す設計とする。
    """

    model_config = ConfigDict(frozen=True)

    big5: Big5Values
    biography_id: int = Field(
        ge=0, description="同梱の経歴プールへのインデックス。0..19 のいずれか。"
    )
    prompt_variant: Literal["A", "B", "C"] = "A"
    style: StyleParams | None = Field(
        default=None,
        description="文体パラメータの明示指定。None なら Big5 から自動推論。",
    )
    name: str | None = Field(
        default=None,
        description="ログやデバッグ用の表示名。プロンプトには含めない。",
    )

    def to_persona_spec(self, language: Literal["en", "ja", "zh"]) -> PersonaSpec:
        """内部の PersonaSpec に変換する。"""
        return PersonaSpec(
            profile_id=self.name or "persona",
            big5_values=self.big5,
            biographic_description_id=self.biography_id,
            prompt_variant=self.prompt_variant,
            language=language,
            style=self.style,
        )
