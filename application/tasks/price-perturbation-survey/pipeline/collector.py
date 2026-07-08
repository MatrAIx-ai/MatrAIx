"""Decision collection for the price-perturbation survey.

Runs a batch of rendered prompts through a model callable, parses each
JSON response, and returns structured ``Decision`` objects.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Sequence

from .perturbation import Perturbation
from .renderer import RenderedPrompt

logger = logging.getLogger(__name__)

# Type alias: the model callable receives (system_prompt, user_prompt)
# and returns the raw text response.  ``system_prompt`` may be ``None``.
ModelCallable = Callable[[str | None, str], str]

# Purchase-intent scale (Nielsen/Ipsos/Qualtrics-style 5-point scale).
# "Top-2-box" (definitely/probably would buy) maps to would_buy="yes";
# the rest map to "no", preserving the binary retention-rate metric.
_TOP_2_BOX = {"definitely_would_buy", "probably_would_buy"}
_VALID_PURCHASE_INTENT = _TOP_2_BOX | {
    "might_or_might_not",
    "probably_would_not",
    "definitely_would_not",
}
_VALID_PRICE_FAIRNESS = {
    "much_too_high",
    "somewhat_high",
    "about_right",
    "good_value",
    "great_value",
}
_VALID_PURCHASE_TIMING = {"buy_now", "wait_for_sale", "not_planning_to_buy"}
_VALID_NECESSITY_LEVEL = {
    "essential",
    "important_but_not_urgent",
    "nice_to_have",
}


@dataclass(frozen=True)
class ParsedSurvey:
    """The validated fields extracted from one survey response."""

    purchase_intent: str
    would_buy: str
    price_fairness: str
    alternative_seeking: str
    purchase_timing: str
    necessity_level: str
    reasoning: str


@dataclass(frozen=True)
class Decision:
    """A single persona's purchase decision for one product.

    Attributes
    ----------
    product_name:
        The product being evaluated.
    persona_id:
        Identifier for the persona, or ``None`` for non-persona runs.
    would_buy:
        ``"yes"`` or ``"no"`` — derived from ``purchase_intent`` via
        top-2-box scoring (see ``parse_decision``).
    reasoning:
        The persona's stated reasoning.
    raw_response:
        The full raw text returned by the model (for debugging).
    purchase_intent, price_fairness, alternative_seeking, purchase_timing,
    necessity_level:
        The full consumer purchase-intent survey response. ``None`` only
        for decisions built outside ``collect_decisions`` (e.g. tests).
    """

    product_name: str
    persona_id: str | None
    would_buy: str
    reasoning: str
    raw_response: str
    perturbation: Perturbation | None = None
    purchase_intent: str | None = None
    price_fairness: str | None = None
    alternative_seeking: str | None = None
    purchase_timing: str | None = None
    necessity_level: str | None = None


def _require_enum(data: dict, field: str, allowed: set[str]) -> str:
    value = data.get(field)
    if value not in allowed:
        raise ValueError(
            f"{field!r} must be one of {sorted(allowed)}, got {value!r}"
        )
    return value


def parse_decision(raw: str) -> ParsedSurvey:
    """Extract and validate the six survey fields from a model response.

    The model is instructed to output a JSON object with the consumer
    purchase-intent survey fields (see ``instruction.md``). This function
    handles both bare JSON and JSON embedded in markdown code fences.

    Raises
    ------
    ValueError
        If the response cannot be parsed or has invalid field values.
    """
    text = raw.strip()

    # Strip optional markdown code fences.
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening and closing fence lines.
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}")

    purchase_intent = _require_enum(data, "purchase_intent", _VALID_PURCHASE_INTENT)
    price_fairness = _require_enum(data, "price_fairness", _VALID_PRICE_FAIRNESS)
    alternative_seeking = _require_enum(data, "alternative_seeking", {"yes", "no"})
    purchase_timing = _require_enum(data, "purchase_timing", _VALID_PURCHASE_TIMING)
    necessity_level = _require_enum(data, "necessity_level", _VALID_NECESSITY_LEVEL)

    reasoning = data.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("'reasoning' must be a non-empty string")

    would_buy = "yes" if purchase_intent in _TOP_2_BOX else "no"

    return ParsedSurvey(
        purchase_intent=purchase_intent,
        would_buy=would_buy,
        price_fairness=price_fairness,
        alternative_seeking=alternative_seeking,
        purchase_timing=purchase_timing,
        necessity_level=necessity_level,
        reasoning=reasoning,
    )


def collect_decisions(
    prompts: Sequence[RenderedPrompt],
    model_fn: ModelCallable,
) -> list[Decision]:
    """Run each prompt through the model and collect decisions.

    Parameters
    ----------
    prompts:
        Rendered prompts (one per product-persona pair).
    model_fn:
        A callable ``(system_prompt, user_prompt) -> response_text``.
        This indirection makes the collector testable without a live
        LLM — callers can pass a mock or stub.

    Returns
    -------
    list[Decision]
        One ``Decision`` per prompt.  If a response fails to parse, the
        error is logged and the prompt is skipped (the decision list may
        be shorter than the prompt list).
    """
    decisions: list[Decision] = []
    for prompt in prompts:
        try:
            raw = model_fn(prompt.system_prompt, prompt.user_prompt)
        except Exception:
            logger.exception(
                "Model call failed for product=%s persona=%s",
                prompt.product_name,
                prompt.persona_id,
            )
            continue

        try:
            parsed = parse_decision(raw)
        except ValueError:
            logger.exception(
                "Failed to parse response for product=%s persona=%s: %.200s",
                prompt.product_name,
                prompt.persona_id,
                raw,
            )
            continue

        decisions.append(
            Decision(
                product_name=prompt.product_name,
                persona_id=prompt.persona_id,
                would_buy=parsed.would_buy,
                reasoning=parsed.reasoning,
                raw_response=raw,
                perturbation=prompt.perturbation,
                purchase_intent=parsed.purchase_intent,
                price_fairness=parsed.price_fairness,
                alternative_seeking=parsed.alternative_seeking,
                purchase_timing=parsed.purchase_timing,
                necessity_level=parsed.necessity_level,
            )
        )
    return decisions
