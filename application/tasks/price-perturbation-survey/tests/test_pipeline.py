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

def _survey_response(**overrides: str) -> str:
    """Build a valid six-field survey JSON response, with overrides."""
    data = {
        "purchase_intent": "probably_would_buy",
        "price_fairness": "about_right",
        "alternative_seeking": "no",
        "purchase_timing": "buy_now",
        "necessity_level": "important_but_not_urgent",
        "reasoning": "Good value.",
    }
    data.update(overrides)
    return json.dumps(data)


def _mock_model_alternating(system_prompt: str | None, user_prompt: str) -> str:
    """Return alternating yes/no decisions based on prompt content.

    Uses a simple hash of the user_prompt to decide deterministically.
    """
    if hash(user_prompt) % 2 == 0:
        return _survey_response(
            purchase_intent="probably_would_buy",
            reasoning="The price increase is manageable given the product quality.",
        )
    return _survey_response(
        purchase_intent="probably_would_not",
        price_fairness="somewhat_high",
        alternative_seeking="yes",
        purchase_timing="wait_for_sale",
        reasoning="The new price exceeds what I am comfortable paying.",
    )


def _mock_model_always_yes(system_prompt: str | None, user_prompt: str) -> str:
    return _survey_response(
        purchase_intent="definitely_would_buy",
        price_fairness="good_value",
        necessity_level="essential",
        reasoning="I still want this product regardless of the price bump.",
    )


def _mock_model_always_no(system_prompt: str | None, user_prompt: str) -> str:
    return _survey_response(
        purchase_intent="definitely_would_not",
        price_fairness="much_too_high",
        alternative_seeking="yes",
        purchase_timing="not_planning_to_buy",
        necessity_level="nice_to_have",
        reasoning="This is simply too expensive for my budget now.",
    )


# ---------------------------------------------------------------------------
# Unit tests — individual components
# ---------------------------------------------------------------------------

class TestProduct:
    def test_fixture_source_loads_products(self) -> None:
        source = FixtureProductSource()
        products = source.get_products()
        assert len(products) == 6
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
        raw = _survey_response(purchase_intent="definitely_would_buy")
        parsed = parse_decision(raw)
        assert parsed.would_buy == "yes"
        assert parsed.purchase_intent == "definitely_would_buy"
        assert parsed.reasoning == "Good value."

    def test_parse_decision_fenced_json(self) -> None:
        raw = "```json\n" + _survey_response(
            purchase_intent="definitely_would_not", reasoning="Too pricey."
        ) + "\n```"
        parsed = parse_decision(raw)
        assert parsed.would_buy == "no"
        assert parsed.reasoning == "Too pricey."

    def test_parse_decision_top_2_box_mapping(self) -> None:
        expected = {
            "definitely_would_buy": "yes",
            "probably_would_buy": "yes",
            "might_or_might_not": "no",
            "probably_would_not": "no",
            "definitely_would_not": "no",
        }
        for intent, want in expected.items():
            parsed = parse_decision(_survey_response(purchase_intent=intent))
            assert parsed.would_buy == want

    def test_parse_decision_invalid_purchase_intent(self) -> None:
        raw = _survey_response(purchase_intent="maybe")
        with pytest.raises(ValueError, match="purchase_intent"):
            parse_decision(raw)

    def test_parse_decision_invalid_price_fairness(self) -> None:
        raw = _survey_response(price_fairness="not_a_value")
        with pytest.raises(ValueError, match="price_fairness"):
            parse_decision(raw)

    def test_parse_decision_invalid_alternative_seeking(self) -> None:
        raw = _survey_response(alternative_seeking="maybe")
        with pytest.raises(ValueError, match="alternative_seeking"):
            parse_decision(raw)

    def test_parse_decision_invalid_purchase_timing(self) -> None:
        raw = _survey_response(purchase_timing="someday")
        with pytest.raises(ValueError, match="purchase_timing"):
            parse_decision(raw)

    def test_parse_decision_invalid_necessity_level(self) -> None:
        raw = _survey_response(necessity_level="kind_of_need_it")
        with pytest.raises(ValueError, match="necessity_level"):
            parse_decision(raw)

    def test_parse_decision_empty_reasoning(self) -> None:
        raw = _survey_response(reasoning="")
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
        assert result.prompts_rendered == 6  # 6 fixture products
        assert len(result.decisions) == 6
        assert result.prompts_failed == 0
        assert result.retention_rate == 1.0
        for d in result.decisions:
            assert d.would_buy == "yes"
            assert d.reasoning

    def test_pipeline_with_personas(self) -> None:
        """Pipeline runs with 2 personas × 6 products = 12 prompts."""
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
        assert result.prompts_rendered == 12  # 6 products × 2 personas
        assert len(result.decisions) == 12
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
