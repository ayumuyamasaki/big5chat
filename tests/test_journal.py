"""Tests for JSONL journal writer."""

import json

from big5chat.dialogue.providers.base import LLMResponse
from big5chat.journal import JsonlJournal
from big5chat.persona.spec import Big5Values, PersonaSpec


def test_journal_writes_turn(tmp_path):
    path = tmp_path / "test.jsonl"
    spec = PersonaSpec(
        profile_id="t", big5_values=Big5Values(O=1, C=1, E=1, A=1, N=1),
        biographic_description_id=0, item_postamble_id=0, language="ja",
    )
    resp = LLMResponse(
        content="hi", model_id="m", provider="p", seed=42, temperature=0.0,
    )
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    with JsonlJournal(path, "exp1") as j:
        j.log_turn(persona_spec=spec, messages=msgs, response=resp, turn_idx=0)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["experiment_id"] == "exp1"
    assert rec["turn_idx"] == 0
    assert rec["persona_hash"] == spec.profile_hash()
    assert rec["response"]["content"] == "hi"
    assert "entry_hash" in rec


def test_journal_events_appended(tmp_path):
    path = tmp_path / "ev.jsonl"
    with JsonlJournal(path) as j:
        j.log_event("start", {"x": 1})
        j.log_event("stop", {"x": 2})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec_a = json.loads(lines[0])
    rec_b = json.loads(lines[1])
    assert rec_a["event_type"] == "start"
    assert rec_b["event_type"] == "stop"
