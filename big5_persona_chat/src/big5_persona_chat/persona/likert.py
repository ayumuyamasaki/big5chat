"""9 段階 Likert 修飾語の表現。

ConstructionPlan.md §C.2:
    +4: extremely  / 非常に / 极其
    +3: very       / とても / 非常
    +2: quite      / かなり / 相当
    +1: a bit      / 少し   / 有点
     0: neutral
    -1..-4: a bit..extremely [反対極]
"""

from __future__ import annotations

LIKERT_EN_POSITIVE = {4: "extremely", 3: "very", 2: "quite", 1: "a bit"}
LIKERT_EN_NEGATIVE = {-1: "a bit", -2: "quite", -3: "very", -4: "extremely"}

LIKERT_JA_POSITIVE = {4: "非常に", 3: "とても", 2: "かなり", 1: "少し"}
LIKERT_JA_NEGATIVE = {-1: "あまり", -2: "かなり", -3: "ほとんど", -4: "まったく"}

LIKERT_ZH_POSITIVE = {4: "极其", 3: "非常", 2: "相当", 1: "有点"}
LIKERT_ZH_NEGATIVE = {-1: "有点", -2: "相当", -3: "非常", -4: "极其"}


def likert_phrase_en(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """例: 'very talkative, energetic, outgoing, ...'。"""
    if value > 0:
        mod = LIKERT_EN_POSITIVE[value]
        return f"{mod} {', '.join(high_markers)}"
    if value < 0:
        mod = LIKERT_EN_POSITIVE[-value]
        return f"{mod} {', '.join(low_markers)}"
    return f"neither particularly {high_markers[0]} nor {low_markers[0]}"


def likert_phrase_ja(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """例: 'とても社交的で、話好きで、陽気な'。"""
    if value > 0:
        mod = LIKERT_JA_POSITIVE[value]
        return mod + "、".join(high_markers)
    if value < 0:
        mod = LIKERT_JA_POSITIVE[-value]
        return mod + "、".join(low_markers)
    return f"{high_markers[0]}でも{low_markers[0]}でもない"


def likert_phrase_zh(value: int, high_markers: list[str], low_markers: list[str]) -> str:
    """例: '非常外向的、健谈的、活跃的'。"""
    if value > 0:
        mod = LIKERT_ZH_POSITIVE[value]
        return mod + "、".join(high_markers)
    if value < 0:
        mod = LIKERT_ZH_POSITIVE[-value]
        return mod + "、".join(low_markers)
    return f"既不{high_markers[0]}也不{low_markers[0]}"


def english_intensifier(value: int) -> str:
    if value > 0:
        return LIKERT_EN_POSITIVE[value]
    if value < 0:
        return LIKERT_EN_POSITIVE[-value]
    return "neither"


def japanese_intensifier(value: int) -> str:
    if value > 0:
        return LIKERT_JA_POSITIVE[value]
    if value < 0:
        return LIKERT_JA_POSITIVE[-value]
    return "どちらでもない"


def chinese_intensifier(value: int) -> str:
    if value > 0:
        return LIKERT_ZH_POSITIVE[value]
    if value < 0:
        return LIKERT_ZH_POSITIVE[-value]
    return "中立"


def likert_phrase(value: int, high_markers: list[str], low_markers: list[str], language: str) -> str:
    """言語ディスパッチヘルパ。"""
    if language == "zh":
        return likert_phrase_zh(value, high_markers, low_markers)
    if language == "ja":
        return likert_phrase_ja(value, high_markers, low_markers)
    return likert_phrase_en(value, high_markers, low_markers)
