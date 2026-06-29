"""Tests for the price-perturbation survey pipeline.

Runs the full pipeline end-to-end on the fixture product source with a
deterministic mock model — no network calls, no LLM API key required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the pipeline package is importable regardless of where pytest
# is invoked from.
_TASK_DIR = Path(__file__).resolve().parent.parent
_PIPELINE_DIR = _TASK_DIR / "pipeline"
if str(_TASK_DIR) not in sys.path:
    sys.path.insert(0, str(_TASK_DIR))

from pipeline.collector import Decision, parse_decision
from pipeline.metrics import compute_retention_rate
from pipeline.models import Product
from pipeline.perturbation import perturb_price
from pipeline.product_source import FixtureProductSource
from pipeline.renderer import RenderedPrompt, render_instruction, render_prompt
from pipeline.run import PipelineResult, run_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_model_alternating(system_prompt: str | None, user_prompt: str) -> str:
    """Return alternating yes/no decisions based on prompt content.

    Uses a simple hash of the user_prompt to decide deterministically.
    """
    if hash(user_prompt) % 2 == 0:
        decision = "yes"
        reasoning = "The price increase is manageable given the product quality."
    else:
        decision = "no"
        reasoning = "The new price exceeds what I am comfortable paying."
    return json.dumps({"would_buy": decision, "reasoning": reasoning})


def _mock_model_always_yes(system_prompt: str | None, user_prompt: str) -> str:
    return json.dumps({
        "would_buy": "yes",
        "reasoning": "I still want this product regardless of the price bump.",
    })


def _mock_model_always_no(system_prompt: str | None, user_prompt: str) -> str:
    return json.dumps({
        "would_buy": "no",
        "reasoning": "This is simply too expensive for my budget now.",
    })


# ---------------------------------------------------------------------------
# Unit tests — individual components
# ---------------------------------------------------------------------------

class TestProduct:
    def test_fixture_source_loads_products(self) -> None:
        source = FixtureProductSource()
        products = source.get_products()
        assert len(products) == 5
        for p in products:
            assert isinstance(p, Product)
            assert p.product_name
            assert p.description
            assert p.original_price > 0

    def test_perturb_price_25_percent(self) -> None:
        product = Product(
            product_name="Widget",
            description="A test widget",
            original_price=100.00,
        )
        assert perturb_price(product) == 125.00

    def test_perturb_price_rounding(self) -> None:
        product = Product(
            product_name="Gizmo",
            description="A test gizmo",
            original_price=44.99,
        )
        # 44.99 * 1.25 = 56.2375 → 56.24
        assert perturb_price(product) == 56.24


class TestRenderer:
    def test_render_instruction_fills_placeholders(self) -> None:
        product = Product(
            product_name="Test Shoes",
            description="Comfortable running shoes",
            original_price=100.00,
        )
        text = render_instruction(product)
        assert "{{product_name}}" not in text
        assert "{{product_description}}" not in text
        assert "{{original_price}}" not in text
        assert "{{new_price}}" not in text
        assert "Test Shoes" in text
        assert "Comfortable running shoes" in text
        assert "100.00" in text
        assert "125.00" in text

    def test_render_prompt_includes_persona(self) -> None:
        product = Product(
            product_name="Gadget",
            description="A useful gadget",
            original_price=50.00,
        )
        rp = render_prompt(
            product,
            persona_system_prompt="You are a frugal shopper.",
            persona_id="P001",
        )
        assert isinstance(rp, RenderedPrompt)
        assert rp.system_prompt == "You are a frugal shopper."
        assert rp.persona_id == "P001"
        assert rp.product_name == "Gadget"
        assert "Gadget" in rp.user_prompt


class TestCollector:
    def test_parse_decision_bare_json(self) -> None:
        raw = '{"would_buy": "yes", "reasoning": "Good value."}'
        wb, reasoning = parse_decision(raw)
        assert wb == "yes"
        assert reasoning == "Good value."

    def test_parse_decision_fenced_json(self) -> None:
        raw = '```json\n{"would_buy": "no", "reasoning": "Too pricey."}\n```'
        wb, reasoning = parse_decision(raw)
        assert wb == "no"
        assert reasoning == "Too pricey."

    def test_parse_decision_invalid_would_buy(self) -> None:
        raw = '{"would_buy": "maybe", "reasoning": "Not sure."}'
        with pytest.raises(ValueError, match="would_buy"):
            parse_decision(raw)

    def test_parse_decision_empty_reasoning(self) -> None:
        raw = '{"would_buy": "yes", "reasoning": ""}'
        with pytest.raises(ValueError, match="reasoning"):
            parse_decision(raw)


class TestMetrics:
    def test_retention_rate_all_yes(self) -> None:
        decisions = [
            Decision("A", "P1", "yes", "reason", "{}"),
            Decision("B", "P2", "yes", "reason", "{}"),
        ]
        assert compute_retention_rate(decisions) == 1.0

    def test_retention_rate_all_no(self) -> None:
        decisions = [
            Decision("A", "P1", "no", "reason", "{}"),
            Decision("B", "P2", "no", "reason", "{}"),
        ]
        assert compute_retention_rate(decisions) == 0.0

    def test_retention_rate_mixed(self) -> None:
        decisions = [
            Decision("A", "P1", "yes", "reason", "{}"),
            Decision("B", "P2", "no", "reason", "{}"),
            Decision("C", "P3", "yes", "reason", "{}"),
        ]
        assert abs(compute_retention_rate(decisions) - 2 / 3) < 1e-9

    def test_retention_rate_empty(self) -> None:
        assert compute_retention_rate([]) == 0.0


# ---------------------------------------------------------------------------
# Integration test — full pipeline
# ---------------------------------------------------------------------------

class TestPipelineEndToEnd:
    """Run the full pipeline on fixture products with mock models."""

    def test_pipeline_with_no_personas(self) -> None:
        """Pipeline runs without personas (one prompt per product)."""
        result = run_pipeline(
            source=FixtureProductSource(),
            model_fn=_mock_model_always_yes,
        )
        assert isinstance(result, PipelineResult)
        assert result.prompts_rendered == 5  # 5 fixture products
        assert len(result.decisions) == 5
        assert result.prompts_failed == 0
        assert result.retention_rate == 1.0
        for d in result.decisions:
            assert d.would_buy == "yes"
            assert d.reasoning

    def test_pipeline_with_personas(self) -> None:
        """Pipeline runs with 2 personas × 5 products = 10 prompts."""
        personas = {
            "budget_buyer": "You are a budget-conscious shopper.",
            "enthusiast": "You are a tech enthusiast who values quality.",
        }
        result = run_pipeline(
            source=FixtureProductSource(),
            model_fn=_mock_model_alternating,
            persona_prompts=personas,
        )
        assert isinstance(result, PipelineResult)
        assert result.prompts_rendered == 10  # 5 products × 2 personas
        assert len(result.decisions) == 10
        assert result.prompts_failed == 0
        assert 0.0 <= result.retention_rate <= 1.0

    def test_pipeline_all_no(self) -> None:
        """Retention rate is 0.0 when nobody buys."""
        result = run_pipeline(
            source=FixtureProductSource(),
            model_fn=_mock_model_always_no,
        )
        assert result.retention_rate == 0.0
        for d in result.decisions:
            assert d.would_buy == "no"

    def test_pipeline_decisions_have_correct_fields(self) -> None:
        """Every Decision object has non-empty required fields."""
        result = run_pipeline(
            source=FixtureProductSource(),
            model_fn=_mock_model_always_yes,
        )
        for d in result.decisions:
            assert isinstance(d, Decision)
            assert d.product_name
            assert d.would_buy in ("yes", "no")
            assert d.reasoning
            assert d.raw_response

    def test_pipeline_result_counts_consistent(self) -> None:
        """prompts_rendered == len(decisions) + prompts_failed."""
        result = run_pipeline(
            source=FixtureProductSource(),
            model_fn=_mock_model_always_yes,
        )
        assert result.prompts_rendered == len(result.decisions) + result.prompts_failed
