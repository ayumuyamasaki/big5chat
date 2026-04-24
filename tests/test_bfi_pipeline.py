"""Integration test: BFI pipeline end-to-end with MockProvider."""

import pytest

from big5chat.evaluation.bfi import BFIEvaluator


@pytest.mark.asyncio
async def test_bfi_pipeline_with_mock(mock_provider, sample_spec_ja):
    mock_provider.next_response = "4"
    evaluator = BFIEvaluator(
        mock_provider, postambles=[0], variants=["A"], n_reps=1, max_concurrency=4
    )
    result = await evaluator.evaluate(sample_spec_ja, seed_base=42)
    # Every item parsed should be 4; reversed items become 6-4=2
    # So dim means should be between 2 and 4.
    for dim in ["O", "C", "E", "A", "N"]:
        assert 1.5 <= result.dim_scores[dim] <= 4.5
        assert result.dim_n[dim] > 0
    assert len(result.raw) > 0


@pytest.mark.asyncio
async def test_bfi_reverses_correctly(mock_provider, sample_spec_ja):
    # If all responses are "5" (strongly agree), reversed items should score 6-5=1
    mock_provider.next_response = "5"
    evaluator = BFIEvaluator(
        mock_provider, postambles=[0], variants=["A"], n_reps=1, max_concurrency=4
    )
    result = await evaluator.evaluate(sample_spec_ja, seed_base=42)
    # Each dim has 2 direct + 2 reversed items => mean = (5+5+1+1)/4 = 3
    for dim in ["O", "C", "E", "A", "N"]:
        assert abs(result.dim_scores[dim] - 3.0) < 0.01
