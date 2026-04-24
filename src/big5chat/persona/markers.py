"""Big5 adjective markers for High / Low poles.

Sources:
- English: McCrae & John (1992) trait adjectives, IPIP-NEO pool.
- Japanese: 和田 1996 BFS, 並川 2012 短縮版, BFI-2-J (Yoshino 2022).
- Simplified Chinese: CBF-PI (王孟成 et al. 2011) style adjective vocabulary.
"""

from __future__ import annotations

MARKERS_EN: dict[str, dict[str, list[str]]] = {
    "O": {
        "high": ["curious", "imaginative", "insightful", "original", "artistic",
                 "creative", "adventurous", "inquisitive"],
        "low": ["uncreative", "uninquisitive", "traditional", "conventional",
                "unimaginative", "narrow-minded", "unreflective", "practical"],
    },
    "C": {
        "high": ["efficient", "organized", "reliable", "responsible", "thorough",
                 "hardworking", "planful", "self-disciplined"],
        "low": ["lazy", "disorganized", "careless", "irresponsible", "inefficient",
                "impulsive", "negligent", "undependable"],
    },
    "E": {
        "high": ["talkative", "energetic", "outgoing", "assertive", "active",
                 "enthusiastic", "bold", "gregarious"],
        "low": ["silent", "reserved", "quiet", "shy", "withdrawn",
                "unenergetic", "introverted", "passive"],
    },
    "A": {
        "high": ["kind", "sympathetic", "generous", "forgiving", "cooperative",
                 "altruistic", "trusting", "warm"],
        "low": ["cold", "unkind", "uncooperative", "harsh", "antagonistic",
                "rude", "distrustful", "selfish"],
    },
    "N": {
        "high": ["anxious", "tense", "worrying", "touchy", "self-pitying",
                 "unstable", "moody", "fearful"],
        "low": ["emotionally stable", "calm", "relaxed", "easygoing", "confident",
                "secure", "contented", "even-tempered"],
    },
}


MARKERS_JA: dict[str, dict[str, list[str]]] = {
    "O": {
        "high": ["好奇心の強い", "独創的な", "進歩的な", "多才な", "想像力に富んだ",
                 "興味の広い", "美的感覚の鋭い", "洞察力のある"],
        "low": ["発想力に欠けた", "平凡な", "伝統的な", "想像力のない", "保守的な",
                "視野の狭い", "内省的でない", "実利的な"],
    },
    "C": {
        "high": ["計画性のある", "几帳面な", "勤勉な", "真面目な", "責任感のある",
                 "しっかりとした", "粘り強い", "自制的な"],
        "low": ["いい加減な", "ルーズな", "怠惰な", "軽率な", "成り行き任せの",
                "だらしない", "衝動的な", "無責任な"],
    },
    "E": {
        "high": ["社交的な", "話好きな", "陽気な", "外向的な", "活動的な",
                 "積極的な", "活発な", "明るい"],
        "low": ["無口な", "ひかえめな", "意思表示を控える", "おとなしい", "内気な",
                "控えめな", "内省的な", "物静かな"],
    },
    "A": {
        "high": ["温和な", "寛大な", "親切な", "協力的な", "やさしい",
                 "思いやりのある", "素直な", "誠実な"],
        "low": ["短気な", "怒りっぽい", "自己中心的な", "反抗的な", "冷淡な",
                "不信感の強い", "批判的な", "つっけんどんな"],
    },
    "N": {
        "high": ["不安になりやすい", "心配性な", "弱気な", "緊張しやすい", "憂鬱な",
                 "神経質な", "動揺しやすい", "気分屋な"],
        "low": ["冷静で気分が安定した", "楽天的な", "リラックスした", "安心感のある",
                "落ち着いた", "ストレスに強い", "自信のある", "感情の起伏が少ない"],
    },
}


# Simplified Chinese markers - phrase form, already suitable for `〜的` connector.
MARKERS_ZH: dict[str, dict[str, list[str]]] = {
    "O": {
        "high": ["富有想象力的", "好奇的", "有创造性的", "开放的", "富有艺术感的",
                 "独立思考的", "富有洞察力的", "具有冒险精神的"],
        "low": ["缺乏想象力的", "保守的", "传统的", "务实的", "视野狭窄的",
                "刻板的", "循规蹈矩的", "实际的"],
    },
    "C": {
        "high": ["有条理的", "勤奋的", "可靠的", "有责任感的", "细致的",
                 "有计划性的", "自律的", "尽职尽责的"],
        "low": ["懒散的", "杂乱的", "粗心的", "不负责任的", "拖延的",
                "马虎的", "缺乏自律的", "随意的"],
    },
    "E": {
        "high": ["健谈的", "精力充沛的", "外向的", "自信的", "活跃的",
                 "热情的", "大胆的", "善于社交的"],
        "low": ["沉默寡言的", "内敛的", "安静的", "害羞的", "内向的",
                "低调的", "不善社交的", "被动的"],
    },
    "A": {
        "high": ["善良的", "富有同情心的", "慷慨的", "宽容的", "合作的",
                 "利他的", "信任他人的", "温和的"],
        "low": ["冷漠的", "不友善的", "不合作的", "苛刻的", "对抗性强的",
                "粗鲁的", "多疑的", "自私的"],
    },
    "N": {
        "high": ["焦虑的", "紧张的", "爱担心的", "敏感的", "情绪化的",
                 "容易沮丧的", "神经质的", "心神不宁的"],
        "low": ["情绪稳定的", "冷静的", "放松的", "随和的", "有安全感的",
                "满足的", "沉着的", "不易动摇的"],
    },
}


def get_markers(language: str, dim: str, polarity: str, n: int = 5) -> list[str]:
    """Return up to `n` markers for the given dimension and polarity."""
    if language == "zh":
        pool = MARKERS_ZH
    elif language == "ja":
        pool = MARKERS_JA
    else:
        pool = MARKERS_EN
    return pool[dim][polarity][:n]
