"""JSONL journal writer with per-entry hashing for tamper-detection."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from big5chat.dialogue.providers.base import LLMResponse
from big5chat.persona.spec import PersonaSpec


def hash_dict(obj: Any) -> str:
    """Short stable hash (first 16 hex chars of sha256)."""
    blob = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class JsonlJournal:
    """Append-only JSONL writer.

    One line per LLM call. Each line is a JSON object with a stable schema
    designed for post-hoc replay and audit.
    """

    def __init__(self, path: Path | str, experiment_id: str | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.experiment_id = experiment_id or self.path.stem
        self._fh = self.path.open("a", encoding="utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        if not self._fh.closed:
            self._fh.flush()
            self._fh.close()

    def log_turn(
        self,
        *,
        persona_spec: PersonaSpec,
        messages: list[dict[str, str]],
        response: LLMResponse,
        turn_idx: int,
        subject_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one dialogue-turn record. Returns the written dict."""
        persona_dump = persona_spec.model_dump()
        entry: dict[str, Any] = {
            "ts_ns": time.time_ns(),
            "experiment_id": self.experiment_id,
            "subject_id": subject_id,
            "turn_idx": turn_idx,
            "persona_hash": persona_spec.profile_hash(),
            "persona_spec": persona_dump,
            "messages_hash": hash_dict(messages),
            "messages": messages,
            "response": {
                "content": response.content,
                "model_id": response.model_id,
                "provider": response.provider,
                "seed": response.seed,
                "system_fingerprint": response.system_fingerprint,
                "temperature": response.temperature,
                "top_p": response.top_p,
                "stop_reason": response.stop_reason,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "logprobs": [lp.model_dump() for lp in response.logprobs],
            },
            "extra": extra or {},
        }
        entry["entry_hash"] = hash_dict(entry)
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()
        return entry

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append an arbitrary non-turn event (e.g., experiment start/end)."""
        entry = {
            "ts_ns": time.time_ns(),
            "experiment_id": self.experiment_id,
            "event_type": event_type,
            "payload": payload,
        }
        entry["entry_hash"] = hash_dict(entry)
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()
