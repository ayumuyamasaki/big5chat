"""Three semantically-equivalent prompt lead-ins (ConstructionPlan.md §D.5).

Using 3 paraphrases counters prompt sensitivity (Gupta 2024).
"""

from __future__ import annotations

PROMPT_VARIANTS_EN: dict[str, str] = {
    "A": 'For the following conversation, respond in a way that matches this description:',
    "B": "Play the role of a person described as follows:",
    "C": "Respond as someone who would describe themselves like this:",
}

PROMPT_VARIANTS_JA: dict[str, str] = {
    "A": "以下の会話で、あなたは次の人物像にあった応答をしてください：",
    "B": "次のように自己紹介する人物の役を演じてください：",
    "C": "以下の人物像にあたる人として応答してください：",
}

PROMPT_VARIANTS_ZH: dict[str, str] = {
    "A": "在接下来的对话中，请以符合以下人物描述的方式进行回复：",
    "B": "请扮演一个自我介绍如下的人物：",
    "C": "请以符合以下人物描述的人的身份进行回复：",
}


def variant(language: str, key: str) -> str:
    if language == "zh":
        pool = PROMPT_VARIANTS_ZH
    elif language == "ja":
        pool = PROMPT_VARIANTS_JA
    else:
        pool = PROMPT_VARIANTS_EN
    return pool[key]
