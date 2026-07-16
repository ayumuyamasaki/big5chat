"""Tests for persona layer."""

import pytest

from big5chat.persona.likert import (
    likert_phrase_en,
    likert_phrase_ja,
)
from big5chat.persona.markers import MARKERS_EN, MARKERS_JA, get_markers
from big5chat.persona.spec import Big5Values, PersonaSpec, StyleParams


def test_big5_values_in_range():
    Big5Values(O=4, C=1, E=3, A=2, N=5)
    with pytest.raises(Exception):
        Big5Values(O=6, C=3, E=3, A=3, N=3)
    with pytest.raises(Exception):
        Big5Values(O=0, C=3, E=3, A=3, N=3)


def test_persona_hash_stability():
    spec1 = PersonaSpec(
        profile_id="p1",
        big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0,
        item_postamble_id=0,
    )
    spec2 = PersonaSpec(
        profile_id="p1",
        big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0,
        item_postamble_id=0,
    )
    assert spec1.profile_hash() == spec2.profile_hash()
    spec3 = spec1.with_updates(big5_values=Big5Values(O=5, C=2, E=5, A=4, N=1))
    assert spec1.profile_hash() != spec3.profile_hash()


def test_ja_default_style_applied():
    spec = PersonaSpec(
        profile_id="p", big5_values=Big5Values(O=4, C=2, E=5, A=4, N=1),
        biographic_description_id=0, item_postamble_id=0, language="ja",
    )
    assert spec.style is not None
    assert spec.style.first_person in {"私", "僕", "俺", "わたし", "自分", "あたし"}


def test_likert_phrase_ja_positive():
    high = ["社交的な", "話好きな", "陽気な"]
    low = ["無口な", "ひかえめな", "おとなしい"]
    s = likert_phrase_ja(5, high, low)
    assert s.startswith("非常に")
    assert "社交的な" in s


def test_likert_phrase_ja_negative():
    high = ["社交的な", "話好きな", "陽気な"]
    low = ["無口な", "ひかえめな", "おとなしい"]
    s = likert_phrase_ja(1, high, low)
    assert s.startswith("全く")
    assert "無口な" in s


def test_likert_phrase_en_positive():
    high = ["talkative", "energetic", "outgoing"]
    low = ["silent", "reserved", "quiet"]
    s = likert_phrase_en(5, high, low)
    assert s.startswith("extremely")
    assert "talkative" in s


def test_markers_complete():
    for dim in ["O", "C", "E", "A", "N"]:
        assert len(MARKERS_JA[dim]["high"]) >= 5
        assert len(MARKERS_JA[dim]["low"]) >= 5
        assert len(MARKERS_EN[dim]["high"]) >= 5
        assert len(MARKERS_EN[dim]["low"]) >= 5


def test_get_markers_trimming():
    m = get_markers("ja", "E", "high", 3)
    assert len(m) == 3
