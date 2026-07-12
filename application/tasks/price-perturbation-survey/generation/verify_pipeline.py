#!/usr/bin/env python3
"""Verification run: price-perturbation survey pipeline on real personas.

Loads 3 personas from the repo's bench-dev-sample dataset, constructs
their system prompts using the repo's persona loader and dimension
narrative builder, and runs the full pipeline end-to-end.

Because no LLM API key is available in this environment, the model
callable uses deterministic mock responses that vary by persona to
simulate realistic behavior.  The purpose is to verify that:

  1. Real persona data loads and renders correctly.
  2. The pipeline orchestrates the full flow without errors.
  3. The retention-rate metric is computed correctly.

Results are saved to ``output/verification_results.json``.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── path setup (no editable install needed) ──────────────────────
# This file lives at <repo>/application/tasks/price-perturbation-survey/
# generation/verify_pipeline.py — five levels down from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "environment" / "agents" / "personabench" / "agents"))

from persona.loader import load_persona  # noqa: E402
from personabench.persona_dimension_catalog import build_dimension_narrative  # noqa: E402

# Pipeline imports (relative to this task directory)
TASK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TASK_DIR))
from pipeline.product_source import FixtureProductSource  # noqa: E402
from pipeline.run import run_pipeline  # noqa: E402

# ── configuration ────────────────────────────────────────────────

# Three personas from bench-dev-sample (chosen for demographic variety).
PERSONA_IDS = ["0001", "0042", "0052"]
PERSONA_DIR = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample"
OUTPUT_DIR = TASK_DIR / "output"


def _build_system_prompt(persona_path: Path) -> tuple[str, str]:
    """Load a persona YAML and build its system prompt.

    Mirrors the logic in ``persona_system.md.j2`` for v2 personas
    with dimensions, without requiring the full Jinja2 template chain
    (which needs an editable package install).

    Returns (persona_id, system_prompt).
    """
    p = load_persona(persona_path)
    narrative = build_dimension_narrative(p.dimensions)

    lines = [
        f"# Simulated person: {p.persona_id} (schema {p.version})",
        "",
        "## Who you are",
        "",
        "The following is your background — read it as a biography "
        "and stay in character.",
        "",
    ]
    for para in narrative:
        lines.append(para)
        lines.append("")
    lines.append("Stay in character according to all of the above.")
    return p.persona_id, "\n".join(lines)


def _mock_model(system_prompt: str | None, user_prompt: str) -> str:
    """Deterministic mock model that varies response by persona.

    Uses a simple hash of the system prompt to decide yes/no, giving
    a mix of purchase decisions across personas and products.
    """
    # Derive a deterministic seed from the prompt content.
    seed = hash((system_prompt or "", user_prompt)) % 100

    if seed < 55:
        survey = {
            "purchase_intent": "probably_would_buy",
            "price_fairness": "about_right",
            "alternative_seeking": "no",
            "purchase_timing": "buy_now",
            "necessity_level": "important_but_not_urgent",
            "reasoning": (
                "After thinking about it, the price increase isn't too steep "
                "and I genuinely need this product. The quality justifies "
                "the higher cost for me."
            ),
        }
    else:
        survey = {
            "purchase_intent": "probably_would_not",
            "price_fairness": "somewhat_high",
            "alternative_seeking": "yes",
            "purchase_timing": "wait_for_sale",
            "necessity_level": "nice_to_have",
            "reasoning": (
                "The 25% price hike pushes this out of my comfort zone. "
                "I'd rather wait for a sale or look for an alternative "
                "at the original price point."
            ),
        }

    return json.dumps(survey)


def main() -> None:
    """Run the verification pipeline and save results."""
    print("=" * 60)
    print("Price-Perturbation Survey — Verification Run")
    print("=" * 60)
    print()

    # 1. Load personas.
    print(f"Loading {len(PERSONA_IDS)} personas from {PERSONA_DIR.name}/...")
    persona_prompts: dict[str, str] = {}
    for pid in PERSONA_IDS:
        path = PERSONA_DIR / f"persona_{pid}.yaml"
        persona_id, system_prompt = _build_system_prompt(path)
        persona_prompts[persona_id] = system_prompt
        print(f"  ✓ persona_{pid}: {len(system_prompt)} chars")
    print()

    # 2. Run the pipeline.
    print("Running pipeline (fixture products × 3 personas, mock LLM)...")
    source = FixtureProductSource()
    products = source.get_products()
    print(f"  Products: {len(products)}")
    print(f"  Personas: {len(persona_prompts)}")
    print(f"  Expected prompts: {len(products) * len(persona_prompts)}")
    print()

    result = run_pipeline(
        source=source,
        model_fn=_mock_model,
        persona_prompts=persona_prompts,
    )

    # 3. Print results.
    print("Results:")
    print(f"  Prompts rendered:  {result.prompts_rendered}")
    print(f"  Decisions parsed:  {len(result.decisions)}")
    print(f"  Parse failures:    {result.prompts_failed}")
    print(f"  Retention rate:    {result.retention_rate:.2%}")
    print()

    # Per-persona breakdown.
    print("Per-persona breakdown:")
    for pid in PERSONA_IDS:
        pid_decisions = [d for d in result.decisions if d.persona_id == pid]
        yes_count = sum(1 for d in pid_decisions if d.would_buy == "yes")
        total = len(pid_decisions)
        rate = yes_count / total if total else 0.0
        print(f"  persona_{pid}: {yes_count}/{total} would buy ({rate:.0%})")
    print()

    # Per-product breakdown.
    print("Per-product breakdown:")
    for product in products:
        prod_decisions = [
            d for d in result.decisions if d.product_name == product.product_name
        ]
        yes_count = sum(1 for d in prod_decisions if d.would_buy == "yes")
        total = len(prod_decisions)
        rate = yes_count / total if total else 0.0
        print(f"  {product.product_name}: {yes_count}/{total} ({rate:.0%})")
    print()

    # 4. Save to JSON.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "verification_results.json"

    output_data = {
        "run_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": "mock (deterministic, no API key available)",
            "personas": PERSONA_IDS,
            "product_count": len(products),
            "factor": 1.25,
        },
        "aggregate": {
            "retention_rate": round(result.retention_rate, 4),
            "prompts_rendered": result.prompts_rendered,
            "decisions_collected": len(result.decisions),
            "parse_failures": result.prompts_failed,
        },
        "decisions": [
            {
                "product_name": d.product_name,
                "persona_id": d.persona_id,
                "would_buy": d.would_buy,
                "purchase_intent": d.purchase_intent,
                "price_fairness": d.price_fairness,
                "alternative_seeking": d.alternative_seeking,
                "purchase_timing": d.purchase_timing,
                "necessity_level": d.necessity_level,
                "reasoning": d.reasoning,
            }
            for d in result.decisions
        ],
    }

    output_path.write_text(json.dumps(output_data, indent=2) + "\n")
    print(f"Results saved to {output_path.relative_to(TASK_DIR)}")
    print()
    print("NOTE: This run used a deterministic mock model because no")
    print("LLM API key was available. The mock varies responses based")
    print("on prompt content to produce a realistic mix of decisions.")
    print("A live run with ANTHROPIC_API_KEY would use actual LLM")
    print("persona reasoning.")


if __name__ == "__main__":
    main()
