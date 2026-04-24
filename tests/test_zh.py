"""Tests for Simplified Chinese (zh) language support."""

import pytest

from big5chat.persona.likert import (
    likert_phrase_zh,
    chinese_intensifier,
)
from big5chat.persona.markers import MARKERS_ZH, get_markers
from big5chat.persona.biographies import BIOGRAPHIES_ZH, get_biography
from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler
from big5chat.prompts.postambles import POSTAMBLES_ZH, postamble
from big5chat.prompts.variants import PROMPT_VARIANTS_ZH
from big5chat.safety.constraints import safety_preamble


def test_markers_zh_complete():
    for dim in ["O", "C", "E", "A", "N"]:
        assert len(MARKERS_ZH[dim]["high"]) >= 5
        assert len(MARKERS_ZH[dim]["low"]) >= 5


def test_biographies_zh_len():
    assert len(BIOGRAPHIES_ZH) >= 15


def test_get_markers_zh():
    m = get_markers("zh", "E", "high", 3)
    assert len(m) == 3
    assert any("外向" in x for x in m) or any("健谈" in x for x in m)


def test_likert_phrase_zh_positive():
    high = MARKERS_ZH["E"]["high"][:3]
    low = MARKERS_ZH["E"]["low"][:3]
    s = likert_phrase_zh(3, high, low)
    assert s.startswith("非常")
    assert high[0] in s


def test_likert_phrase_zh_negative():
    high = MARKERS_ZH["E"]["high"][:3]
    low = MARKERS_ZH["E"]["low"][:3]
    s = likert_phrase_zh(-3, high, low)
    assert s.startswith("非常")
    assert low[0] in s


def test_chinese_intensifier():
    assert chinese_intensifier(4) == "极其"
    assert chinese_intensifier(-4) == "极其"
    assert chinese_intensifier(0) == "中立"


def test_prompt_variants_zh():
    assert set(PROMPT_VARIANTS_ZH) == {"A", "B", "C"}
    for v in PROMPT_VARIANTS_ZH.values():
        assert any(ch in v for ch in ["请", "对话", "人物"])


def test_postambles_zh():
    assert len(POSTAMBLES_ZH) == 5
    for i in range(5):
        assert postamble("zh", i) == POSTAMBLES_ZH[i]


def test_persona_spec_zh_default_style():
    spec = PersonaSpec(
        profile_id="zh_test",
        big5_values=Big5Values(O=2, C=1, E=3, A=2, N=-2),
        biographic_description_id=0,
        item_postamble_id=0,
        prompt_variant="A",
        language="zh",
    )
    assert spec.style is not None
    assert spec.style.first_person in {"我", "咱"}
    assert spec.style.sentence_ending in {"书面", "口语", "混合", "随意"}


def test_assembler_zh():
    spec = PersonaSpec(
        profile_id="zh_test",
        big5_values=Big5Values(O=2, C=1, E=3, A=2, N=-2),
        biographic_description_id=0,
        item_postamble_id=0,
        prompt_variant="A",
        language="zh",
    )
    assembler = PromptAssembler()
    prompt = assembler.assemble(spec)
    assert "对话" in prompt or "人物" in prompt
    assert "的人" in prompt
    assert "第一人称" in prompt
    assert len(prompt) > 200


def test_persona_summary_zh():
    spec = PersonaSpec(
        profile_id="zh_test",
        big5_values=Big5Values(O=2, C=1, E=3, A=2, N=-2),
        biographic_description_id=0,
        item_postamble_id=0,
        language="zh",
    )
    assembler = PromptAssembler()
    summary = assembler.persona_summary(spec)
    assert len(summary) > 10
    assert summary.count("、") >= 4


def test_reinjection_message_zh():
    spec = PersonaSpec(
        profile_id="zh_test",
        big5_values=Big5Values(O=2, C=1, E=3, A=2, N=-2),
        biographic_description_id=0,
        item_postamble_id=0,
        language="zh",
    )
    assembler = PromptAssembler()
    msg = assembler.reinjection_message(spec)
    assert "重要提示" in msg
    assert "人物形象" in msg


def test_safety_preamble_zh_high_n():
    spec = PersonaSpec(
        profile_id="zh_high_n",
        big5_values=Big5Values(O=0, C=0, E=0, A=0, N=3),
        biographic_description_id=0,
        item_postamble_id=0,
        language="zh",
    )
    preamble = safety_preamble(spec.big5_values, "zh")
    assert preamble is not None
    assert "自杀" in preamble


def test_biography_zh_wraps():
    bio1 = get_biography("zh", 0)
    bio_wrap = get_biography("zh", len(BIOGRAPHIES_ZH))
    assert bio1 == bio_wrap
