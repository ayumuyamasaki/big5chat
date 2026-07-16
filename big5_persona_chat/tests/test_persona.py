"""Big5 / Persona / PersonaSpec のバリデーションと変換ロジックの検証。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from big5_persona_chat.persona import Big5, Persona
from big5_persona_chat.persona.spec import StyleParams


def test_big5_accepts_full_range():
    # -4 .. +4 の全域が許容される (README/pptx 記載の値域)
    big5 = Big5(O=4, C=-4, E=0, A=3, N=-3)
    assert big5.as_dict() == {"O": 4, "C": -4, "E": 0, "A": 3, "N": -3}


@pytest.mark.parametrize("field,value", [("O", 5), ("C", -5), ("N", 100)])
def test_big5_rejects_out_of_range(field, value):
    kwargs = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
    kwargs[field] = value
    with pytest.raises(ValidationError):
        Big5(**kwargs)


def test_persona_to_persona_spec_uses_name_as_profile_id():
    persona = Persona(big5=Big5(O=1, C=1, E=1, A=1, N=1), biography_id=0, name="MY_BOT")
    spec = persona.to_persona_spec("ja")
    assert spec.profile_id == "MY_BOT"
    assert spec.language == "ja"
    assert spec.biographic_description_id == 0
    assert spec.big5_values == persona.big5


def test_persona_to_persona_spec_defaults_profile_id_when_name_none():
    persona = Persona(big5=Big5(O=0, C=0, E=0, A=0, N=0), biography_id=0)
    spec = persona.to_persona_spec("en")
    assert spec.profile_id == "persona"


def test_extravert_leader_style_auto_inference_matches_pptx_slide9(extravert_leader):
    """pptxスライド9: 'EXTRAVERT_LEADER (E=+3, A=+1) なら、何も指定しなくても
    自動で「僕・混合文末・終助詞高め・絵文字少々」という文体になります' の検証。
    """
    spec = extravert_leader.to_persona_spec("ja")
    assert spec.style is not None
    assert spec.style.first_person == "僕"
    assert spec.style.sentence_ending == "混合"
    assert spec.style.particle_frequency == "高"
    assert spec.style.emoji == "少"


def test_introvert_thinker_style_auto_inference(introvert_thinker):
    # E=-3 (低外向) のため、砕けた一人称/絵文字にはならない
    spec = introvert_thinker.to_persona_spec("ja")
    assert spec.style is not None
    assert spec.style.first_person == "私"
    assert spec.style.particle_frequency == "低"
    assert spec.style.emoji == "無"


def test_explicit_style_overrides_auto_inference(extravert_leader):
    custom_style = StyleParams(first_person="わたし", sentence_ending="敬体")
    persona = extravert_leader.model_copy(update={"style": custom_style})
    spec = persona.to_persona_spec("ja")
    assert spec.style is custom_style
    assert spec.style.first_person == "わたし"


def test_style_auto_inference_not_applied_for_english():
    # README: style は en では使われない (常に None のまま)
    persona = Persona(big5=Big5(O=2, C=2, E=3, A=1, N=-2), biography_id=2)
    spec = persona.to_persona_spec("en")
    assert spec.style is None
