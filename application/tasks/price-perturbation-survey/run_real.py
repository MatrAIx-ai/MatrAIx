#!/usr/bin/env python3
"""Real pipeline run: price and attribute perturbation survey.

Loads 4 diverse personas from the repo's bench-dev-sample dataset and
runs the extended pipeline (multi-attribute perturbation: price, color,
shape, material) using llama3.1 via Ollama (local, zero API cost).

Tuned for laptops: small context window (2048), inter-call delay,
and configurable product count to control total runtime.

Results are saved to ``output/real_run_results.json``.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── path setup ────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(
    0,
    str(REPO_ROOT / "environment" / "agents" / "personabench" / "agents"),
)

from persona.loader import load_persona  # noqa: E402
from personabench.persona_dimension_catalog import (  # noqa: E402
    build_dimension_narrative,
)

# Pipeline imports
TASK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TASK_DIR))
from pipeline.collector import Decision  # noqa: E402
from pipeline.product_source import FixtureProductSource  # noqa: E402
from pipeline.run import run_pipeline_extended  # noqa: E402

# ── configuration ─────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:latest"

# Low-resource / unattended-run tuning: cap CPU threads per generation
# (machine has 8 physical cores; 2 leaves 6 fully free) and pause between
# calls so the machine is mostly idle rather than continuously busy.
# Calls already run strictly sequentially (no concurrency) below.
NUM_THREAD = 2
INTER_CALL_DELAY_SEC = 5

# Four personas chosen for demographic and economic-motivation diversity.
#   0042: 55-64, upper-middle, cautious/analytical — "indifferent" spender
#   0052: 13-17, middle income, cost-sensitive — budget-constrained
#   0666: 25-34, middle income, premium-seeking — willing to pay more
#   0712: 25-34, middle income, value-driven — wants bang for buck
PERSONA_IDS = ["0042", "0052", "0666", "0712"]
PERSONA_DIR = REPO_ROOT / "persona" / "datasets" / "bench-dev-sample"
OUTPUT_DIR = TASK_DIR / "output"

PRODUCTS_PATH = TASK_DIR / "fixtures" / "products.json"

# Cap the number of products to evaluate (None = use all).
# For local Ollama, keep this small to avoid multi-day runs.
MAX_PRODUCTS: int | None = None


# ── persona prompt construction ───────────────────────────────────

def build_system_prompt(persona_path: Path) -> tuple[str, str]:
    """Load a persona YAML and build its system prompt."""
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


# ── Ollama model callable ────────────────────────────────────────

_call_count = 0


def ollama_model_fn(system_prompt: str | None, user_prompt: str) -> str:
    """Call llama3.1 via Ollama's local REST API."""
    global _call_count
    _call_count += 1

    full_prompt_parts: list[str] = []
    if system_prompt:
        full_prompt_parts.append(system_prompt)
    full_prompt_parts.append(user_prompt)
    full_prompt_parts.append(
        '\nIMPORTANT: Respond with ONLY a valid JSON object, no other text. '
        'Format: {"purchase_intent": "definitely_would_buy" | "probably_would_buy" '
        '| "might_or_might_not" | "probably_would_not" | "definitely_would_not", '
        '"price_fairness": "much_too_high" | "somewhat_high" | "about_right" | '
        '"good_value" | "great_value", '
        '"alternative_seeking": "yes" or "no", '
        '"purchase_timing": "buy_now" | "wait_for_sale" | "not_planning_to_buy", '
        '"necessity_level": "essential" | "important_but_not_urgent" | "nice_to_have", '
        '"reasoning": "your reasoning"}'
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": "\n\n".join(full_prompt_parts),
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 250,
            "num_ctx": 2048,
            # Cap CPU threads per call so a single generation never
            # monopolizes the machine — trades speed for a low, steady
            # footprint suitable for an unattended overnight run.
            "num_thread": NUM_THREAD,
        },
    }

    if _call_count % 10 == 0:
        print(f"  ... call {_call_count} in progress")

    resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
    resp.raise_for_status()
    result = resp.json()["response"]

    # Deliberate pause between calls (in addition to the thread cap) so
    # the machine spends most of its time idle, not just throttled.
    time.sleep(INTER_CALL_DELAY_SEC)
    return result


# ── display helpers ───────────────────────────────────────────────

def print_trajectories(
    decisions: list[Decision],
    persona_ids: list[str],
) -> None:
    """Print full per-persona, per-product decision trajectories."""
    print("\n" + "=" * 70)
    print("DECISION TRAJECTORIES")
    print("=" * 70)

    for pid in persona_ids:
        pid_decisions = [d for d in decisions if d.persona_id == pid]
        print(f"\n{'─' * 70}")
        print(f"  PERSONA: {pid}")
        print(f"{'─' * 70}")

        for d in pid_decisions:
            verdict = "BUY" if d.would_buy == "yes" else "PASS"
            perturb_desc = "N/A"
            if d.perturbation:
                p = d.perturbation
                perturb_desc = (
                    f"{p.attribute}: {p.original_value} -> {p.new_value}"
                )

            print(f"\n  Product:      {d.product_name}")
            print(f"  Perturbation: {perturb_desc}")
            print(f"  Decision:     [{verdict}] ({d.purchase_intent})")
            print(f"  Price:        {d.price_fairness}  |  Timing: {d.purchase_timing}  |  "
                  f"Necessity: {d.necessity_level}  |  Seeks alt: {d.alternative_seeking}")
            print(f"  Reason:       {d.reasoning}")

    print(f"\n{'=' * 70}\n")


def print_breakdown(
    decisions: list[Decision],
    persona_ids: list[str],
) -> None:
    """Print aggregate breakdowns."""
    print("PER-PERSONA RETENTION:")
    for pid in persona_ids:
        pid_decisions = [d for d in decisions if d.persona_id == pid]
        yes = sum(1 for d in pid_decisions if d.would_buy == "yes")
        total = len(pid_decisions)
        rate = yes / total if total else 0.0
        print(f"  persona_{pid}: {yes}/{total} would buy ({rate:.0%})")

    print("\nPER-ATTRIBUTE RETENTION:")
    attr_groups: dict[str, list[Decision]] = {}
    for d in decisions:
        attr = d.perturbation.attribute if d.perturbation else "unknown"
        attr_groups.setdefault(attr, []).append(d)
    for attr, group in sorted(attr_groups.items()):
        yes = sum(1 for d in group if d.would_buy == "yes")
        total = len(group)
        rate = yes / total if total else 0.0
        print(f"  {attr}: {yes}/{total} ({rate:.0%})")


# ── main ──────────────────────────────────────────────────────────

def main() -> None:
    factor = 1.25

    print("=" * 70)
    print("Price & Attribute Perturbation Survey — Extended Pipeline")
    print(f"Model: {OLLAMA_MODEL} (local via Ollama, zero API cost)")
    print("=" * 70)
    print()

    # 1. Load personas.
    print(f"Loading {len(PERSONA_IDS)} personas from {PERSONA_DIR.name}/...")
    persona_prompts: dict[str, str] = {}
    for pid in PERSONA_IDS:
        path = PERSONA_DIR / f"persona_{pid}.yaml"
        persona_id, system_prompt = build_system_prompt(path)
        persona_prompts[persona_id] = system_prompt
        print(f"  loaded persona_{pid}: {len(system_prompt)} chars")
    print()

    # 2. Load products.
    source = FixtureProductSource(path=PRODUCTS_PATH)
    products = source.get_products()
    if MAX_PRODUCTS is not None:
        products = products[:MAX_PRODUCTS]
        # Re-wrap as a source that returns the subset.
        class _SubsetSource:
            def __init__(self, prods):
                self._prods = prods
            def get_products(self):
                return self._prods
        source = _SubsetSource(products)

    print(f"Products loaded: {len(products)}")
    total_calls = len(products) * len(persona_prompts)
    print(f"Pipeline: {len(products)} products x "
          f"{len(persona_prompts)} personas = {total_calls} LLM calls")
    print()

    # 3. Run pipeline.
    t0 = time.time()
    result = run_pipeline_extended(
        source=source,
        model_fn=ollama_model_fn,
        persona_prompts=persona_prompts,
        factor=factor,
    )
    elapsed = time.time() - t0

    # 4. Print summary.
    print(f"\nPipeline complete in {elapsed:.1f}s")
    print(f"  Prompts rendered:  {result.prompts_rendered}")
    print(f"  Decisions parsed:  {len(result.decisions)}")
    print(f"  Parse failures:    {result.prompts_failed}")
    print(f"  RETENTION RATE:    {result.retention_rate:.2%}")
    print()

    # 5. Print trajectories (cap output for large runs).
    if len(result.decisions) <= 100:
        print_trajectories(result.decisions, PERSONA_IDS)
    else:
        print(f"({len(result.decisions)} decisions — showing first 40)")
        print_trajectories(result.decisions[:40], PERSONA_IDS)

    # 6. Print breakdowns.
    print_breakdown(result.decisions, PERSONA_IDS)

    # 7. Save to JSON.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "real_run_results.json"

    per_persona_retention = {}
    for pid in PERSONA_IDS:
        pid_decisions = [
            d for d in result.decisions if d.persona_id == pid
        ]
        yes = sum(1 for d in pid_decisions if d.would_buy == "yes")
        total = len(pid_decisions)
        per_persona_retention[pid] = {
            "yes": yes,
            "total": total,
            "retention_rate": round(yes / total, 4) if total else 0.0,
        }

    per_attribute_retention = {}
    for d in result.decisions:
        attr = d.perturbation.attribute if d.perturbation else "unknown"
        bucket = per_attribute_retention.setdefault(
            attr, {"yes": 0, "total": 0}
        )
        bucket["total"] += 1
        if d.would_buy == "yes":
            bucket["yes"] += 1
    for bucket in per_attribute_retention.values():
        t = bucket["total"]
        bucket["retention_rate"] = round(bucket["yes"] / t, 4) if t else 0.0

    output_data = {
        "run_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": OLLAMA_MODEL,
            "model_backend": "ollama (local)",
            "personas": PERSONA_IDS,
            "product_count": len(products),
            "factor": factor,
            "elapsed_seconds": round(elapsed, 1),
        },
        "aggregate": {
            "retention_rate": round(result.retention_rate, 4),
            "prompts_rendered": result.prompts_rendered,
            "decisions_collected": len(result.decisions),
            "parse_failures": result.prompts_failed,
        },
        "per_persona_retention": per_persona_retention,
        "per_attribute_retention": per_attribute_retention,
        "decisions": [
            {
                "product_name": d.product_name,
                "persona_id": d.persona_id,
                "perturbation": {
                    "attribute": d.perturbation.attribute,
                    "original_value": d.perturbation.original_value,
                    "new_value": d.perturbation.new_value,
                } if d.perturbation else None,
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
    print(f"\nResults saved to {output_path.relative_to(TASK_DIR)}")


if __name__ == "__main__":
    main()
