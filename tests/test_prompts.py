"""Tests for prompt assembly."""

from big5chat.persona.spec import Big5Values, PersonaSpec
from big5chat.prompts.assembler import PromptAssembler
from big5chat.prompts.postambles import POSTAMBLES_JA, postamble
from big5chat.prompts.variants import PROMPT_VARIANTS_JA


def test_assembler_ja(sample_spec_ja):
    assembler = PromptAssembler()
    prompt = assembler.assemble(sample_spec_ja)
    assert "以下の会話で" in prompt or "役を演じ" in prompt or "人として応答" in prompt
    assert "人物" in prompt
    assert "一人称" in prompt
    # Should include a biographic fragment
    assert len(prompt) > 200


def test_assembler_en(sample_spec_en):
    assembler = PromptAssembler()
    prompt = assembler.assemble(sample_spec_en)
    assert "Maintain this personality" in prompt
    assert "I am" in prompt


def test_variants_complete():
    assert set(PROMPT_VARIANTS_JA) == {"A", "B", "C"}


def test_postambles_count():
    assert len(POSTAMBLES_JA) == 5
    for i in range(5):
        assert postamble("ja", i) == POSTAMBLES_JA[i]


def test_persona_summary_nonempty(sample_spec_ja):
    assembler = PromptAssembler()
    summary = assembler.persona_summary(sample_spec_ja)
    assert len(summary) > 10
    # All 5 dims' phrases should be joined
    assert summary.count("、") >= 4


def test_reinjection_message_contains_summary(sample_spec_ja):
    assembler = PromptAssembler()
    msg = assembler.reinjection_message(sample_spec_ja)
    assert "【重要リマインド】" in msg
    assert "現在のあなたの人物像" in msg


def test_safety_preamble_in_high_N():
    spec = PersonaSpec(
        profile_id="pN",
        big5_values=Big5Values(O=0, C=0, E=0, A=0, N=3),
        biographic_description_id=0,
        item_postamble_id=0,
        language="ja",
    )
    assembler = PromptAssembler()
    from big5chat.safety.constraints import safety_preamble
    preamble = safety_preamble(spec.big5_values, "ja")
    assert preamble is not None
    prompt = assembler.assemble(spec, safety_preamble=preamble)
    assert "自殺" in prompt
