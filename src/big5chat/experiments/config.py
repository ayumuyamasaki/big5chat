"""Experiment configuration loader (YAML-driven)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from big5chat.persona.spec import Big5Values, PersonaSpec, StyleParams


class PersonaConfig(BaseModel):
    profile_id: str
    big5_values: Big5Values
    biographic_description_id: int = 0
    item_postamble_id: int = 0
    prompt_variant: str = "A"
    language: str = "ja"
    style: StyleParams | None = None
    n_markers_per_dim: int = 5

    def to_persona_spec(self) -> PersonaSpec:
        return PersonaSpec(
            profile_id=self.profile_id,
            big5_values=self.big5_values,
            biographic_description_id=self.biographic_description_id,
            item_postamble_id=self.item_postamble_id,
            prompt_variant=self.prompt_variant,  # type: ignore[arg-type]
            language=self.language,  # type: ignore[arg-type]
            style=self.style,
            n_markers_per_dim=self.n_markers_per_dim,
        )


class ExperimentConfig(BaseModel):
    experiment_id: str
    description: str = ""
    language: str = "ja"
    primary_model: str = "openai:gpt-4.1"
    judge_models: list[str] = Field(default_factory=lambda: ["openai:gpt-4.1"])
    personas: list[PersonaConfig]
    n_reps: int = 1
    seed_base: int = 42
    max_concurrency: int = 10
    run_bfi: bool = True
    run_expert_rating: bool = True
    run_trait_mcq: bool = True
    output_dir: str = "./results"
    log_dir: str = "./logs"
    # BFIアイテムファイル名テンプレート。"{lang}" を含む場合は実行時に
    # 各ペルソナの言語で置換される。Noneなら既存の bfi2_{lang}.json を使用。
    bfi_items_filename: str | None = None

    @classmethod
    def from_yaml(cls, path: Path | str) -> "ExperimentConfig":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)


def load_config(path: Path | str) -> ExperimentConfig:
    return ExperimentConfig.from_yaml(path)


def generate_32_profiles(
    language: str = "ja",
    amplitude: int = 3,
    biographies_per_profile: int = 1,
) -> list[PersonaConfig]:
    """Generate the 32 binary high/low profiles (PersonaLLM style).

    Each dim is set to +amplitude or -amplitude, giving 2^5 = 32 configs.
    Useful for Phase 0 pilot per ConstructionPlan §H.1.
    """
    import itertools

    configs: list[PersonaConfig] = []
    for idx, bits in enumerate(itertools.product([1, -1], repeat=5)):
        vals = {
            dim: bit * amplitude
            for dim, bit in zip(["O", "C", "E", "A", "N"], bits)
        }
        profile_id = "".join(
            f"{'H' if bit == 1 else 'L'}{dim}"
            for dim, bit in zip(["O", "C", "E", "A", "N"], bits)
        )
        configs.append(
            PersonaConfig(
                profile_id=f"{profile_id}_{idx:02d}",
                big5_values=Big5Values(**vals),
                biographic_description_id=idx % 20,
                language=language,
            )
        )
    return configs
