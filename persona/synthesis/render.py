"""Stdlib-only natural-language rendering for persona attribute maps.

Extracted from ``persona/synthesis/scripts/render_personas.py`` so the
Playground backend can render personas without importing numpy. The script
keeps its CLI and re-imports these symbols.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIMS_PATH = REPO_ROOT / "persona" / "schema" / "dimensions.json"

CORE_ORDER = [
    "age_bracket",
    "gender_identity",
    "region",
    "urbanicity",
    "socioeconomic_band",
    "cultural_background",
    "primary_language",
    "english_proficiency",
    "multilingualism",
    "highest_education",
    "academic_field",
    "domain",
    "subject_specialty",
    "seniority",
    "role_function",
    "company_size",
    "years_experience",
    "life_stage",
]

BUCKETS = [
    ("Personality & values", ("Personality", "Values", "Risk & Decision")),
    ("Worldview", ("Worldview",)),
    ("Interests", ("Interests",)),
    ("Skills & tools", ("Expertise", "Skills")),
    ("Lifestyle & health", ("Health", "Behavior", "Demographic: Life", "Demographic: Family")),
    ("Learning", ("Learning",)),
    ("Developer & AI", ("Developer", "Coding", "AI")),
]

EXCLUDE_PREFIX = (
    "apple_primex_dimension_",
    "personahub_dimension_",
    "oasis_dimension_",
    "horizonbench_dimension_",
    "wildchat_",
    "pandora_",
    "personachat_",
    "synthetic_persona_chat_dimension_",
    "nemotron_",
    "wiki_",
)
EXCLUDE_CATEGORY = ("External",)
STATE_IDS = {
    "emotional_state",
    "intent",
    "query_complexity",
    "expertise_gap",
    "tone_expected",
    "trust_level",
    "safety_sensitivity",
    "time_pressure",
    "prior_context",
    "device_context",
    "modality_pref",
    "accessibility_needs",
}


def _fix_articles(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        article, word = match.group(1), match.group(2)
        letters = re.sub(r"[^A-Za-z]", "", word)
        if letters.isupper() and len(letters) >= 2:
            vowel = word[0].upper() in "AEFHILMNORSX"
        else:
            vowel = word[0].lower() in "aeiou"
        new_article = "an" if vowel else "a"
        if article[0].isupper():
            new_article = new_article.capitalize()
        return f"{new_article} {word}"

    return re.sub(r"\b([Aa]n?)\s+([A-Za-z0-9][\w\-/()]*)", repl, text)


def load_dims(path: str | Path = DEFAULT_DIMS_PATH) -> dict[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text())
    return {d["id"]: d for d in data["dimensions"] if "id" in d and "values" in d}


def _is_default(value: Any, default: Any) -> bool:
    if default is None:
        return False
    if isinstance(default, list):
        return value in default
    return value == default


def _clause(dim: dict[str, Any], value: Any) -> str:
    phrase = dim.get("phrase")
    if phrase:
        return phrase.replace("{value}", str(value))
    label = dim.get("label") or dim.get("id", "attribute").replace("_", " ")
    return f"their {label[:1].lower() + label[1:]} is {value}"


def render(
    assignment: dict[str, Any],
    dims: dict[str, dict[str, Any]],
    *,
    max_clauses_per_bucket: int | None = 30,
) -> str:
    core = []
    for dim_id in CORE_ORDER:
        if dim_id in assignment and dim_id in dims:
            value = assignment[dim_id]
            if not _is_default(value, dims[dim_id].get("defaultValue")):
                core.append(_clause(dims[dim_id], value))

    lines = ["A persona " + ", ".join(core) + "."] if core else []
    used = set(CORE_ORDER) | STATE_IDS
    for title, categories in BUCKETS:
        clauses = []
        for dim_id, value in assignment.items():
            if dim_id in used or dim_id not in dims:
                continue
            if dim_id.startswith(EXCLUDE_PREFIX):
                continue
            dim = dims[dim_id]
            category = dim.get("category") or ""
            if category.startswith(EXCLUDE_CATEGORY):
                continue
            if not category.startswith(categories):
                continue
            if _is_default(value, dim.get("defaultValue")):
                continue
            clauses.append(_clause(dim, value))
            used.add(dim_id)
        if clauses:
            if max_clauses_per_bucket is not None and len(clauses) > max_clauses_per_bucket:
                omitted = len(clauses) - max_clauses_per_bucket
                clauses = clauses[:max_clauses_per_bucket]
                clauses.append(f"and {omitted} more salient attributes")
            lines.append(f"{title}: " + "; ".join(clauses) + ".")

    return _fix_articles("\n".join(lines))
