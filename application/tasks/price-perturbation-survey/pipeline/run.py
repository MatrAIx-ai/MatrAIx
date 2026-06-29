"""End-to-end orchestrator for the price-perturbation survey pipeline.

Wires together: product sourcing → price perturbation → prompt rendering
(for each product × persona combination) → decision collection → retention-
rate metric.

Usage::

    from pipeline.run import run_pipeline
    from pipeline.product_source import FixtureProductSource

    result = run_pipeline(
        source=FixtureProductSource(),
        model_fn=my_model_callable,
        persona_prompts={"0001": "You are a …", "0007": "You are a …"},
    )
    print(f"Retention rate: {result.retention_rate:.2%}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .collector import Decision, ModelCallable, collect_decisions
from .metrics import compute_retention_rate
from .product_source import ProductSource
from .renderer import RenderedPrompt, render_prompt


@dataclass(frozen=True)
class PipelineResult:
    """Aggregate output of a full pipeline run.

    Attributes
    ----------
    decisions:
        All successfully parsed purchase decisions.
    retention_rate:
        Fraction of decisions where ``would_buy == "yes"`` (0.0–1.0).
    prompts_rendered:
        Total number of prompts sent to the model.
    prompts_failed:
        Number of prompts whose responses could not be parsed (i.e.
        ``prompts_rendered - len(decisions)``).
    """

    decisions: list[Decision] = field(default_factory=list)
    retention_rate: float = 0.0
    prompts_rendered: int = 0
    prompts_failed: int = 0


def run_pipeline(
    source: ProductSource,
    model_fn: ModelCallable,
    *,
    persona_prompts: Mapping[str, str | None] | None = None,
    factor: float = 1.25,
    template_path: Path | str | None = None,
) -> PipelineResult:
    """Execute the full price-perturbation survey pipeline.

    Parameters
    ----------
    source:
        A ``ProductSource`` providing the products to evaluate.
    model_fn:
        A callable ``(system_prompt, user_prompt) -> response_text``.
    persona_prompts:
        Mapping of ``{persona_id: system_prompt_text}``.  If ``None`` or
        empty, a single non-persona run is performed per product (the
        system prompt is set to ``None``).
    factor:
        Price-perturbation factor (default 1.25 = +25%).
    template_path:
        Override path to the instruction template.

    Returns
    -------
    PipelineResult
        Aggregated decisions and the rule-based retention rate.
    """
    products = source.get_products()

    # Build the cross-product of (product × persona) prompts.
    rendered: list[RenderedPrompt] = []

    if not persona_prompts:
        # No personas — one prompt per product with no system prompt.
        for product in products:
            rendered.append(
                render_prompt(
                    product,
                    persona_system_prompt=None,
                    persona_id=None,
                    factor=factor,
                    template_path=template_path,
                )
            )
    else:
        for product in products:
            for persona_id, system_prompt in persona_prompts.items():
                rendered.append(
                    render_prompt(
                        product,
                        persona_system_prompt=system_prompt,
                        persona_id=persona_id,
                        factor=factor,
                        template_path=template_path,
                    )
                )

    decisions = collect_decisions(rendered, model_fn)

    return PipelineResult(
        decisions=decisions,
        retention_rate=compute_retention_rate(decisions),
        prompts_rendered=len(rendered),
        prompts_failed=len(rendered) - len(decisions),
    )
