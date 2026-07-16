"""PromptAssembler が3言語でシステムプロンプトを組み立てられることの検証。"""

from __future__ import annotations

import pytest

from big5_persona_chat.persona.biographies import get_biography
from big5_persona_chat.prompts.assembler import PromptAssembler


@pytest.mark.parametrize("language", ["ja", "en", "zh"])
def test_assemble_returns_nonempty_prompt_containing_biography(language, extravert_leader):
    spec = extravert_leader.to_persona_spec(language)
    prompt = PromptAssembler().assemble(spec)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert get_biography(language, spec.biographic_description_id) in prompt


def test_assemble_differs_by_language(extravert_leader):
    assembler = PromptAssembler()
    ja_prompt = assembler.assemble(extravert_leader.to_persona_spec("ja"))
    en_prompt = assembler.assemble(extravert_leader.to_persona_spec("en"))
    assert ja_prompt != en_prompt


def test_persona_summary_is_nonempty(extravert_leader):
    spec = extravert_leader.to_persona_spec("ja")
    summary = PromptAssembler().persona_summary(spec)
    assert isinstance(summary, str)
    assert len(summary) > 0
