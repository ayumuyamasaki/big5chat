"""Tests for TRAIT MCQ evaluator."""

import pytest

from big5chat.evaluation.trait_mcq import (
    TraitMCQEvaluator,
    _extract_option,
    _format_mcq,
)


def test_extract_option():
    assert _extract_option("A") == "A"
    assert _extract_option("答え: B") == "B"
    assert _extract_option("Answer is D.") == "D"
    assert _extract_option("xyz") is None


def test_format_mcq_deterministic():
    import random
    from big5chat.evaluation.trait_mcq import TraitScenario
    scen = TraitScenario(
        id="E01", dim="E",
        situation="foo",
        question="bar?",
        options={"H": "social", "L": "quiet"},
    )
    rng = random.Random(42)
    prompt, mapping = _format_mcq(scen, ["H", "L", "H", "L"], rng)
    assert "A." in prompt and "B." in prompt and "C." in prompt and "D." in prompt
    assert set(mapping) == {"A", "B", "C", "D"}
    assert sum(1 for v in mapping.values() if v == "H") == 2
    assert sum(1 for v in mapping.values() if v == "L") == 2


@pytest.mark.asyncio
async def test_trait_pipeline_with_mock(mock_provider, sample_spec_ja):
    mock_provider.next_response = "A"
    evaluator = TraitMCQEvaluator(mock_provider, max_concurrency=4)
    result = await evaluator.evaluate(sample_spec_ja, seed_base=42)
    assert "E" in result.dim_scores
    # All responses returned "A" letter → chosen pole depends on mapping
    assert 0.0 <= result.dim_scores["E"] <= 1.0
    assert len(result.per_scenario) > 0
