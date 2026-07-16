"""5-stage Likert modifier phrasing (1-5 scale, matching BFI). 3 = neutral.

    5: extremely  / 非常に / 极其
    4: a bit      / 少し   / 有点
    3: neutral
    2: a bit..    / あまり.. / 有点.. [antonym]
    1: extremely.. / 全く.. / 极其.. [antonym]
"""

from __future__ import annotations

# English modifiers (high side keyed by raw value 4/5, low side keyed by raw value 1/2)
LIKERT_EN_POSITIVE = {5: "extremely", 4: "a bit"}
LIKERT_EN_NEGATIVE = {2: "a bit", 1: "extremely"}

# Japanese modifiers
LIKERT_JA_POSITIVE = {5: "非常に", 4: "少し"}
LIKERT_JA_NEGATIVE = {2: "あまり", 1: "全く"}

# Chinese (Simplified) modifiers
LIKERT_ZH_POSITIVE = {5: "极其", 4: "有点"}
LIKERT_ZH_NEGATIVE = {2: "不太", 1: "极其不"}


def likert_phrase_en(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """Return an English phrase like 'very talkative, energetic, outgoing, ...'."""
    if value > 3:
        mod = LIKERT_EN_POSITIVE[value]
        return f"{mod} {', '.join(high_markers)}"
    if value < 3:
        mod = LIKERT_EN_NEGATIVE[value]
        return f"{mod} {', '.join(low_markers)}"
    return f"neither particularly {high_markers[0]} nor {low_markers[0]}"


def likert_phrase_ja(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """Return a Japanese phrase like 'とても社交的で、話好きで、陽気な'."""
    if value > 3:
        mod = LIKERT_JA_POSITIVE[value]
        return mod + "、".join(high_markers)
    if value < 3:
        mod = LIKERT_JA_NEGATIVE[value]
        return mod + "、".join(low_markers)
    return f"{high_markers[0]}でも{low_markers[0]}でもない"


def likert_phrase_zh(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """Return a Chinese phrase like '非常外向的、健谈的、活跃的'."""
    if value > 3:
        mod = LIKERT_ZH_POSITIVE[value]
        return mod + "、".join(high_markers)
    if value < 3:
        mod = LIKERT_ZH_NEGATIVE[value]
        return mod + "、".join(low_markers)
    return f"既不{high_markers[0]}也不{low_markers[0]}"


def english_intensifier(value: int) -> str:
    if value > 3:
        return LIKERT_EN_POSITIVE[value]
    if value < 3:
        return LIKERT_EN_NEGATIVE[value]
    return "neither"


def japanese_intensifier(value: int) -> str:
    if value > 3:
        return LIKERT_JA_POSITIVE[value]
    if value < 3:
        return LIKERT_JA_NEGATIVE[value]
    return "どちらでもない"


def chinese_intensifier(value: int) -> str:
    if value > 3:
        return LIKERT_ZH_POSITIVE[value]
    if value < 3:
        return LIKERT_ZH_NEGATIVE[value]
    return "中立"


def likert_phrase(value: int, high_markers: list[str], low_markers: list[str], language: str) -> str:
    """Dispatch helper."""
    if language == "zh":
        return likert_phrase_zh(value, high_markers, low_markers)
    if language == "ja":
        return likert_phrase_ja(value, high_markers, low_markers)
    return likert_phrase_en(value, high_markers, low_markers)
