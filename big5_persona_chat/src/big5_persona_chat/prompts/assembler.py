"""PromptAssembler: PersonaSpec から送信可能なシステムプロンプトを生成する。

パッケージ同梱の Jinja2 テンプレートを利用する。EN / JA / ZH 対応。
"""

from __future__ import annotations

from importlib import resources

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from big5_persona_chat.persona.likert import (
    likert_phrase_en,
    likert_phrase_ja,
    likert_phrase_zh,
)
from big5_persona_chat.persona.markers import get_markers
from big5_persona_chat.persona.biographies import get_biography
from big5_persona_chat.persona.spec import PersonaSpec
from big5_persona_chat.prompts.variants import variant


_LIKERT_FN = {
    "ja": likert_phrase_ja,
    "zh": likert_phrase_zh,
    "en": likert_phrase_en,
}


class PromptAssembler:
    """PersonaSpec からシステムプロンプトを組み立てるクラス。"""

    def __init__(self, templates_dir: str | None = None):
        if templates_dir is None:
            pkg_root = resources.files("big5_persona_chat.prompts") / "templates"
            templates_dir = str(pkg_root)
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(default=False),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

    def assemble(self, spec: PersonaSpec, safety_preamble: str | None = None) -> str:
        """指定 PersonaSpec に対する完全なシステムプロンプトを返す。"""
        if spec.language == "zh":
            return self._assemble_with_style(spec, safety_preamble, "system_zh.jinja")
        if spec.language == "ja":
            return self._assemble_with_style(spec, safety_preamble, "system_ja.jinja")
        return self._assemble_en(spec, safety_preamble)

    def _assemble_with_style(
        self, spec: PersonaSpec, safety_preamble: str | None, template_name: str
    ) -> str:
        """JA/ZH 共通: style ブロックを使うアセンブリ。"""
        template = self.env.get_template(template_name)
        bio = get_biography(spec.language, spec.biographic_description_id)
        phrase_fn = _LIKERT_FN[spec.language]

        big5_phrases = {
            dim: phrase_fn(
                value=getattr(spec.big5_values, dim),
                high_markers=get_markers(spec.language, dim, "high", spec.n_markers_per_dim),
                low_markers=get_markers(spec.language, dim, "low", spec.n_markers_per_dim),
            )
            for dim in ["O", "C", "E", "A", "N"]
        }

        return template.render(
            variant_lead_in=variant(spec.language, spec.prompt_variant),
            biographic_description=bio,
            big5_O=big5_phrases["O"],
            big5_C=big5_phrases["C"],
            big5_E=big5_phrases["E"],
            big5_A=big5_phrases["A"],
            big5_N=big5_phrases["N"],
            style=spec.style,
            safety_preamble=safety_preamble or "",
        )

    def _assemble_en(self, spec: PersonaSpec, safety_preamble: str | None) -> str:
        template = self.env.get_template("system_en.jinja")
        bio = get_biography("en", spec.biographic_description_id)
        big5_phrases = {
            dim: likert_phrase_en(
                value=getattr(spec.big5_values, dim),
                high_markers=get_markers("en", dim, "high", spec.n_markers_per_dim),
                low_markers=get_markers("en", dim, "low", spec.n_markers_per_dim),
            )
            for dim in ["O", "C", "E", "A", "N"]
        }
        return template.render(
            variant_lead_in=variant("en", spec.prompt_variant),
            biographic_description=bio,
            big5_O=big5_phrases["O"],
            big5_C=big5_phrases["C"],
            big5_E=big5_phrases["E"],
            big5_A=big5_phrases["A"],
            big5_N=big5_phrases["N"],
            safety_preamble=safety_preamble or "",
        )

    def persona_summary(self, spec: PersonaSpec) -> str:
        """再注入リマインダ用の短いサマリ。Big5 句のみを連結する。"""
        phrase_fn = _LIKERT_FN[spec.language]
        parts = []
        for dim in ["O", "C", "E", "A", "N"]:
            parts.append(
                phrase_fn(
                    value=getattr(spec.big5_values, dim),
                    high_markers=get_markers(spec.language, dim, "high", spec.n_markers_per_dim),
                    low_markers=get_markers(spec.language, dim, "low", spec.n_markers_per_dim),
                )
            )
        sep = "、" if spec.language in ("ja", "zh") else "; "
        return sep.join(parts)
