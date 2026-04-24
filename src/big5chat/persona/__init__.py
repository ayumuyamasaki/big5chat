"""Persona construction layer (Layer 1).

Converts a Big5 profile into a structured PersonaSpec usable by the
prompt assembler. Implements Serapio-Garcia 9-stage Likert modifiers.
Supports three languages: en / ja / zh.
"""

from big5chat.persona.spec import Big5Values, PersonaSpec, StyleParams
from big5chat.persona.likert import (
    likert_phrase,
    likert_phrase_en,
    likert_phrase_ja,
    likert_phrase_zh,
)
from big5chat.persona.markers import MARKERS_EN, MARKERS_JA, MARKERS_ZH, get_markers
from big5chat.persona.biographies import (
    BIOGRAPHIES_EN,
    BIOGRAPHIES_JA,
    BIOGRAPHIES_ZH,
    get_biography,
)

__all__ = [
    "Big5Values",
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
]
