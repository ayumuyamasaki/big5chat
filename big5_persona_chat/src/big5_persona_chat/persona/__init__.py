"""ペルソナ構築レイヤ。

- Big5: 5 次元の数値スコア (-4..+4)
- Persona: ユーザー向けの薄いペルソナ仕様(言語非依存)
- PersonaSpec: 内部完全仕様 (言語ロック)
"""

from big5_persona_chat.persona.spec import Big5Values as Big5, PersonaSpec, StyleParams
from big5_persona_chat.persona._user import Persona
from big5_persona_chat.persona.likert import (
    likert_phrase,
    likert_phrase_en,
    likert_phrase_ja,
    likert_phrase_zh,
)
from big5_persona_chat.persona.markers import (
    MARKERS_EN,
    MARKERS_JA,
    MARKERS_ZH,
    get_markers,
)
from big5_persona_chat.persona.biographies import (
    BIOGRAPHIES_EN,
    BIOGRAPHIES_JA,
    BIOGRAPHIES_ZH,
    get_biography,
    n_biographies,
)

__all__ = [
    "Big5",
    "Persona",
    "PersonaSpec",
    "StyleParams",
    "likert_phrase",
    "likert_phrase_en",
    "likert_phrase_ja",
    "likert_phrase_zh",
    "MARKERS_EN",
    "MARKERS_JA",
    "MARKERS_ZH",
    "get_markers",
    "BIOGRAPHIES_EN",
    "BIOGRAPHIES_JA",
    "BIOGRAPHIES_ZH",
    "get_biography",
    "n_biographies",
]
