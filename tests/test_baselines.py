"""Tests for MPI and PersonaLLM baseline adapters."""

from pathlib import Path

import pytest

from big5chat.baselines.mpi import (
    MPI_TEMPLATE,
    MPIEvaluator,
    _parse_mpi_choice,
    load_mpi_inventory,
)
from big5chat.baselines.personallm import (
    PERSONALLM_POLES,
    PersonaLLMEvaluator,
    _parse_bfi_response,
    build_persona_description,
    load_bfi_items,
)
from big5chat.persona.spec import Big5Values, PersonaSpec


ROOT = Path(__file__).resolve().parent.parent
MPI_CSV = ROOT / "external" / "MPI" / "inventories" / "mpi_120.csv"
PERSONALLM_PROMPT = ROOT / "external" / "PersonaLLM" / "prompts" / "bfi_prompt.txt"
PERSONALLM_SCORES = ROOT / "external" / "PersonaLLM" / "prompts" / "bfi_scores.txt"


# --- MPI tests ---

def test_mpi_parse_choice():
    assert _parse_mpi_choice("A") == "A"
    assert _parse_mpi_choice("(B)") == "B"
    assert _parse_mpi_choice("I would choose C.") == "C"
    assert _parse_mpi_choice("xyz") is None


@pytest.mark.skipif(not MPI_CSV.exists(), reason="MPI repo not present")
def test_mpi_inventory_load():
    items = load_mpi_inventory(MPI_CSV)
    assert len(items) == 120
    assert all(it.label_ocean in {"O", "C", "E", "A", "N"} for it in items)
    assert all(it.key in (1, -1) for it in items)


@pytest.mark.asyncio
@pytest.mark.skipif(not MPI_CSV.exists(), reason="MPI repo not present")
async def test_mpi_pipeline_with_mock(mock_provider):
    mock_provider.next_response = "(A). Very Accurate"
    evaluator = MPIEvaluator(
        mock_provider, inventory_path=MPI_CSV, max_concurrency=4
    )
    result = await evaluator.evaluate(persona_spec=None, seed_base=42)
    # All responses=A (score=5, or 1 if key=-1). Dim scores should be in [1, 5].
    for dim in ["O", "C", "E", "A", "N"]:
        assert 1 <= result.dim_mean[dim] <= 5
        assert result.dim_n[dim] > 0


def test_mpi_template_contains_placeholder():
    assert "{text}" in MPI_TEMPLATE
    filled = MPI_TEMPLATE.format(text="worry about things")
    assert "worry about things" in filled
    assert "Very Accurate" in filled


# --- PersonaLLM tests ---

def test_personallm_poles_complete():
    assert set(PERSONALLM_POLES) == {"O", "C", "E", "A", "N"}
    for dim in ["O", "C", "E", "A", "N"]:
        assert 1 in PERSONALLM_POLES[dim]
        assert -1 in PERSONALLM_POLES[dim]


def test_build_persona_description_high():
    big5 = Big5Values(O=3, C=3, E=3, A=3, N=3)
    desc = build_persona_description(big5)
    assert "extroverted" in desc
    assert "agreeable" in desc
    assert "conscientious" in desc
    assert "neurotic" in desc
    assert "and open to experience" in desc


def test_build_persona_description_low():
    big5 = Big5Values(O=-3, C=-3, E=-3, A=-3, N=-3)
    desc = build_persona_description(big5)
    assert "introverted" in desc
    assert "antagonistic" in desc
    assert "unconscientious" in desc
    assert "emotionally stable" in desc
    assert "and closed to experience" in desc


def test_parse_bfi_response_basic():
    raw = "(a) 5\n(b) 3\n(c) 4\n(d) 2\n(e) 1"
    scores = _parse_bfi_response(raw, n_items=5)
    assert scores == [5, 3, 4, 2, 1]


def test_parse_bfi_response_double_letters():
    raw = "(aa) 3\n(bb) 4"
    scores = _parse_bfi_response(raw, n_items=28)
    assert scores[26] == 3  # aa -> idx 26
    assert scores[27] == 4  # bb -> idx 27


@pytest.mark.skipif(
    not (PERSONALLM_PROMPT.exists() and PERSONALLM_SCORES.exists()),
    reason="PersonaLLM repo not present",
)
def test_personallm_scores_load():
    items = load_bfi_items(PERSONALLM_SCORES)
    assert len(items) == 44
    assert all(it.dim in {"O", "C", "E", "A", "N"} for it in items)
    reverse_count = sum(1 for it in items if it.reverse)
    assert 5 <= reverse_count <= 20  # sanity check


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (PERSONALLM_PROMPT.exists() and PERSONALLM_SCORES.exists()),
    reason="PersonaLLM repo not present",
)
async def test_personallm_pipeline_with_mock(mock_provider):
    # Build a fake response covering all 44 items with score 4
    letters = [chr(ord("a") + i) for i in range(26)]
    letters += [f"{chr(ord('a') + i)}{chr(ord('a') + i)}" for i in range(18)]
    fake = "\n".join(f"({l}) 4" for l in letters[:44])
    mock_provider.next_response = fake

    evaluator = PersonaLLMEvaluator(
        mock_provider,
        prompt_path=PERSONALLM_PROMPT,
        scores_path=PERSONALLM_SCORES,
    )
    spec = PersonaSpec(
        profile_id="test",
        big5_values=Big5Values(O=2, C=2, E=3, A=2, N=-2),
        biographic_description_id=0,
        item_postamble_id=0,
        language="en",
    )
    result = await evaluator.evaluate(spec, mode="personallm_native")
    # All parsed scores should be 4 (direct) or 2 (reversed)
    for dim in ["O", "C", "E", "A", "N"]:
        assert 2.0 <= result.dim_mean[dim] <= 4.0
        assert result.dim_n[dim] > 0
