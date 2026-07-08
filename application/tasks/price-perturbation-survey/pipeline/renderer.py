"""Prompt rendering for the price-perturbation survey.

Loads the parameterized ``instruction.md`` template, fills in product-
specific fields (name, description, original price, new +25% price),
and optionally prepends a persona system prompt to produce a complete
prompt pair (system, user) suitable for an LLM call.

Also supports a generalized ``instruction_attribute.md`` template for
non-price attribute perturbations (color, shape, material).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import Product
from .perturbation import Perturbation, perturb_price

_TASK_DIR = Path(__file__).resolve().parent.parent

# instruction.md lives one level above the pipeline/ package.
_INSTRUCTION_TEMPLATE = _TASK_DIR / "instruction.md"
_ATTRIBUTE_TEMPLATE = _TASK_DIR / "instruction_attribute.md"


def _brand_line(product: Product) -> str:
    return product.brand or "N/A"


def _rating_line(product: Product) -> str:
    """Render the customer-rating line, tolerating missing data."""
    if product.rating is None:
        return "No rating data available"
    if product.review_count is None:
        return f"{product.rating:.1f} out of 5 stars"
    return f"{product.rating:.1f} out of 5 stars ({product.review_count:,} ratings)"


@dataclass(frozen=True)
class RenderedPrompt:
    """A fully rendered prompt pair ready for an LLM call.

    Attributes
    ----------
    system_prompt:
        The persona's system prompt (may be ``None`` for non-persona runs).
    user_prompt:
        The task instruction with product fields filled in.
    product_name:
        Name of the product (for bookkeeping / result labeling).
    persona_id:
        Identifier for the persona (for bookkeeping), or ``None``.
    perturbation:
        What was changed about the product (for result recording).
    """

    system_prompt: str | None
    user_prompt: str
    product_name: str
    persona_id: str | None
    perturbation: Perturbation | None = None


def render_instruction(
    product: Product,
    *,
    factor: float = 1.25,
    template_path: Path | str | None = None,
) -> str:
    """Return the instruction text with product fields substituted.

    Parameters
    ----------
    product:
        The product to embed in the instruction.
    factor:
        Price-perturbation factor (default 1.25 = +25%).
    template_path:
        Override path to the instruction template.  Defaults to the
        ``instruction.md`` shipped with this task.
    """
    path = Path(template_path) if template_path is not None else _INSTRUCTION_TEMPLATE
    template_text = path.read_text()

    new_price = perturb_price(product, factor)

    return template_text.replace(
        "{{product_name}}", product.product_name
    ).replace(
        "{{brand}}", _brand_line(product)
    ).replace(
        "{{product_description}}", product.description
    ).replace(
        "{{rating_line}}", _rating_line(product)
    ).replace(
        "{{original_price}}", f"{product.original_price:.2f}"
    ).replace(
        "{{new_price}}", f"{new_price:.2f}"
    )


def render_prompt(
    product: Product,
    *,
    persona_system_prompt: str | None = None,
    persona_id: str | None = None,
    factor: float = 1.25,
    template_path: Path | str | None = None,
) -> RenderedPrompt:
    """Build a complete ``RenderedPrompt`` for one (product, persona) pair.

    Parameters
    ----------
    product:
        The product to evaluate.
    persona_system_prompt:
        The persona's system-level prompt text.  Pass ``None`` to omit
        persona framing (useful for baseline / non-persona runs).
    persona_id:
        A short identifier for the persona (e.g. ``"0001"``).
    factor:
        Price-perturbation factor.
    template_path:
        Override path to the instruction template.
    """
    user_prompt = render_instruction(
        product, factor=factor, template_path=template_path,
    )
    return RenderedPrompt(
        system_prompt=persona_system_prompt,
        user_prompt=user_prompt,
        product_name=product.product_name,
        persona_id=persona_id,
    )


def render_attribute_instruction(
    product: Product,
    perturbation: Perturbation,
    *,
    template_path: Path | str | None = None,
) -> str:
    """Render the generalized attribute-change instruction template."""
    path = (
        Path(template_path) if template_path is not None
        else _ATTRIBUTE_TEMPLATE
    )
    template_text = path.read_text()

    return (
        template_text
        .replace("{{product_name}}", product.product_name)
        .replace("{{brand}}", _brand_line(product))
        .replace("{{product_description}}", product.description)
        .replace("{{rating_line}}", _rating_line(product))
        .replace("{{original_price}}", f"{product.original_price:.2f}")
        .replace("{{attribute_name}}", perturbation.attribute)
        .replace("{{original_value}}", perturbation.original_value)
        .replace("{{new_value}}", perturbation.new_value)
    )


def render_prompt_with_perturbation(
    product: Product,
    perturbation: Perturbation,
    *,
    persona_system_prompt: str | None = None,
    persona_id: str | None = None,
    factor: float = 1.25,
) -> RenderedPrompt:
    """Build a ``RenderedPrompt`` using the appropriate template.

    For price perturbations, uses the original ``instruction.md``.
    For attribute perturbations, uses ``instruction_attribute.md``.
    """
    if perturbation.attribute == "price":
        user_prompt = render_instruction(product, factor=factor)
    else:
        user_prompt = render_attribute_instruction(product, perturbation)

    return RenderedPrompt(
        system_prompt=persona_system_prompt,
        user_prompt=user_prompt,
        product_name=product.product_name,
        persona_id=persona_id,
        perturbation=perturbation,
    )
