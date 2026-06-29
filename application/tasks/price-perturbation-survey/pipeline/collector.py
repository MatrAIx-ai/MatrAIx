"""Decision collection for the price-perturbation survey.

Runs a batch of rendered prompts through a model callable, parses each
JSON response, and returns structured ``Decision`` objects.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Sequence

from .renderer import RenderedPrompt

logger = logging.getLogger(__name__)

# Type alias: the model callable receives (system_prompt, user_prompt)
# and returns the raw text response.  ``system_prompt`` may be ``None``.
ModelCallable = Callable[[str | None, str], str]


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
        ``"yes"`` or ``"no"``.
    reasoning:
        The persona's stated reasoning.
    raw_response:
        The full raw text returned by the model (for debugging).
    """

    product_name: str
    persona_id: str | None
    would_buy: str
    reasoning: str
    raw_response: str


def parse_decision(raw: str) -> tuple[str, str]:
    """Extract ``(would_buy, reasoning)`` from a model response.

    The model is instructed to output a JSON object.  This function
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

    would_buy = data.get("would_buy")
    reasoning = data.get("reasoning")

    if would_buy not in ("yes", "no"):
        raise ValueError(
            f"'would_buy' must be \"yes\" or \"no\", got {would_buy!r}"
        )
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError("'reasoning' must be a non-empty string")

    return would_buy, reasoning


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
            would_buy, reasoning = parse_decision(raw)
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
                would_buy=would_buy,
                reasoning=reasoning,
                raw_response=raw,
            )
        )
    return decisions
