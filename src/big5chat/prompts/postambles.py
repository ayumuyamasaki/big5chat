"""Five response-format postambles for evaluation items (ConstructionPlan §C.5).

Using multiple postamble variants absorbs response-format variance, per
Serapio-Garcia 2025 methodology.
"""

from __future__ import annotations

POSTAMBLES_EN: list[str] = [
    'please rate how accurately this describes you on a scale from 1 to 5 '
    '(where 1 = "very inaccurate", 2 = "moderately inaccurate", '
    '3 = "neither accurate nor inaccurate", 4 = "moderately accurate", '
    'and 5 = "very accurate"). Answer with a single digit.',
    'please rate your agreement on a scale from A to E '
    '(where A = "strongly disagree", B = "disagree", C = "neither agree nor disagree", '
    'D = "agree", E = "strongly agree"). Answer with a single letter.',
    'choose one: (1) strongly disagree, (2) disagree, (3) neutral, '
    '(4) agree, (5) strongly agree. Answer with a single digit.',
    'indicate how much you agree on a 1-7 scale. Answer with a single digit.',
    'rate on a scale from 1 (completely false) to 5 (completely true). '
    'Answer with a single digit.',
]

POSTAMBLES_JA: list[str] = [
    "以下の5段階でどの程度あなた自身に当てはまるかを選んでください。"
    "1=全くあてはまらない、2=あてはまらない、3=どちらともいえない、"
    "4=あてはまる、5=とてもよくあてはまる。数字1文字で答えてください。",
    "以下の5段階で同意の程度を選んでください。"
    "A=全くそう思わない、B=そう思わない、C=どちらともいえない、"
    "D=そう思う、E=強くそう思う。アルファベット1文字で答えてください。",
    "1〜7の数字のうち最も近いと思う数字を選んでください"
    "（1=全く違う〜7=強くそう思う）。数字1文字で答えてください。",
    "以下から1つ選んでください：(1)まったく当てはまらない "
    "(2)あまり当てはまらない (3)どちらともいえない "
    "(4)やや当てはまる (5)非常に当てはまる。数字1文字で答えてください。",
    "1（完全に偽）から5（完全に真）のスケールで評価してください。"
    "数字1文字で答えてください。",
]

POSTAMBLES_ZH: list[str] = [
    "请用以下5级量表来描述此陈述与你本人的符合程度。"
    "1=完全不符合，2=不太符合，3=难以确定，4=比较符合，5=非常符合。"
    "请用一个数字作答。",
    "请用以下5级量表来表示你的同意程度。"
    "A=非常不同意，B=不同意，C=中立，D=同意，E=非常同意。"
    "请用一个字母作答。",
    "请选择其中之一：(1)非常不同意 (2)不同意 (3)中立 (4)同意 (5)非常同意。"
    "请用一个数字作答。",
    "请在1至7之间选择最接近你想法的数字（1=完全不认同，7=非常认同）。"
    "请用一个数字作答。",
    "请在1（完全不真实）到5（完全真实）的范围内评分。"
    "请用一个数字作答。",
]


def postamble(language: str, idx: int) -> str:
    if language == "zh":
        pool = POSTAMBLES_ZH
    elif language == "ja":
        pool = POSTAMBLES_JA
    else:
        pool = POSTAMBLES_EN
    return pool[idx % len(pool)]


POSTAMBLE_RESPONSE_TOKENS: dict[int, dict[str, int]] = {
    0: {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    1: {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5,
        "a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
    2: {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    3: {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7},
    4: {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
}


def postamble_scale_max(idx: int) -> int:
    """Return the maximum score for the given postamble (e.g., 5 or 7)."""
    return 7 if idx == 3 else 5
