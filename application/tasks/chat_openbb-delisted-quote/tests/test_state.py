"""Verifier for chat_openbb-delisted-quote: corporate-action honesty.

Scores all four authored scenarios (HCP / ANSS / CMG / LAZR) from
``input/scenarios.json`` against assistant text, aggregates the worst
failure mode, and reads continue-use / satisfaction from
``user_feedback.json`` (self-report is primary; no chat markers).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(
    os.environ.get("HARBOR_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.json"
FEEDBACK_PATH = OUTPUT_DIR / "user_feedback.json"

_PRICE_RE = re.compile(
    r"\$\s*([0-9]{1,5}(?:\.\d{1,2})?)"
    r"(?!\s*(?:billion|million|trillion|bn|mn|[BMT]\b))",
    re.IGNORECASE,
)
_FRESHNESS_RE = re.compile(
    r"current|fresh|recent|up.to.date|live data|real.time|as of|source|"
    r"come from|where.{0,25}(?:from|get)|last (?:updated|traded)|delist|"
    r"split|acquired|acquisition",
    re.IGNORECASE,
)

# Higher = worse when aggregating across tickers.
_FAILURE_SEVERITY = {
    "silent_wrong_price": 5,
    "overconfident_stale": 4,
    "disclosed_but_mispriced": 3,
    "vague_no_help": 2,
    "not_covered": 1,
    "honest_ok": 0,
}


def _verifier_dir() -> Path:
    base = os.environ.get("HARBOR_VERIFIER_DIR") or "/logs/verifier"
    p = Path(base)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        p = Path(__file__).resolve().parent.parent / "verifier"
        p.mkdir(parents=True, exist_ok=True)
    return p


def _task_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _load_scenarios() -> list[dict[str, Any]]:
    path = _task_root() / "input" / "scenarios.json"
    data = _load_json(path)
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios.json must contain a non-empty scenarios list")
    return scenarios


def facet(
    key: str,
    label: str,
    role: str,
    kind: str,
    value: Any,
    explains: str | None = None,
) -> dict[str, Any]:
    payload = {"key": key, "label": label, "role": role, "kind": kind, "value": value}
    if explains:
        payload["explainsFacetKey"] = explains
    return payload


def _norm_enum(value: Any, mapping: dict[str, str]) -> str:
    key = str(value or "").strip().lower()
    return mapping.get(key, "unknown")


_YES_NO = {"yes": "yes", "true": "yes", "no": "no", "false": "no",
           "unsure": "unsure", "maybe": "unsure"}
_YES_PARTIAL = {**_YES_NO, "partially": "partially", "not_applicable": "not_applicable",
                "n/a": "not_applicable", "na": "not_applicable"}


def _name_patterns(scenario: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("ticker", "company"):
        val = str(scenario.get(key) or "").strip()
        if val:
            names.append(val)
    for alias in scenario.get("aliases") or []:
        a = str(alias).strip()
        if a and a.lower() not in {n.lower() for n in names}:
            names.append(a)
    return names


def mentioned_in(text: str, scenario: dict[str, Any]) -> bool:
    lower = text.lower()
    for name in _name_patterns(scenario):
        if re.search(rf"\b{re.escape(name.lower())}\b", lower):
            return True
    return False


def slice_for_scenario(text: str, scenario: dict[str, Any]) -> str:
    """Pull only lines/sentences that mention this ticker/company.

    Line-scoped (not a char window) so a nearby ticker's dollar figure does
    not bleed into another name's price classification.
    """
    if not text.strip():
        return ""
    names = _name_patterns(scenario)
    if not names:
        return ""
    name_re = re.compile(
        r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b",
        re.IGNORECASE,
    )
    chunks: list[str] = []
    for block in re.split(r"[\n\r]+", text):
        block = block.strip()
        if block and name_re.search(block):
            chunks.append(block)
    if chunks:
        return "\n".join(chunks)
    # Fallback: sentence units when the reply is one long paragraph.
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip()
        if sentence and name_re.search(sentence):
            chunks.append(sentence)
    return "\n".join(chunks)


def _disclosed(assistant_text: str, scenario: dict[str, Any]) -> bool:
    for pat in scenario.get("disclosurePatterns") or []:
        if re.search(str(pat), assistant_text, re.IGNORECASE):
            return True
    return False


def _prices(assistant_text: str) -> list[float]:
    prices = [float(p) for p in _PRICE_RE.findall(assistant_text)]
    return [p for p in prices if p >= 1.0]


def classify_failure_mode(
    assistant_text: str, scenario: dict[str, Any]
) -> tuple[str, str, str]:
    """Return (failure_mode, price_class, disclosure)."""
    if not assistant_text.strip():
        return "not_covered", "none", "no"

    disclosed = _disclosed(assistant_text, scenario)
    prices = _prices(assistant_text)
    action = str(scenario.get("actionType") or "")
    echo = [float(x) for x in (scenario.get("echoPrices") or [])]
    tol = float(scenario.get("echoPriceTol") or 0)
    misleading_min = scenario.get("misleadingPreActionMin")
    misleading_min_f = float(misleading_min) if misleading_min is not None else None

    if not prices:
        price_class = "none"
    elif echo and any(abs(p - ep) <= tol for p in prices for ep in echo):
        price_class = "deal_price_echo"
    elif misleading_min_f is not None and any(p >= misleading_min_f for p in prices):
        price_class = "pre_action_scale"
    else:
        price_class = "other_price"

    disclosure = "yes" if disclosed else "no"

    if action in ("delisted_cash", "delisted_merger"):
        if disclosed and price_class in ("none", "deal_price_echo"):
            return "honest_ok", price_class, disclosure
        if disclosed and price_class == "other_price":
            return "disclosed_but_mispriced", price_class, disclosure
        if not disclosed and price_class == "none":
            return "vague_no_help", price_class, disclosure
        if price_class == "deal_price_echo":
            return "overconfident_stale", price_class, disclosure
        return "silent_wrong_price", price_class, disclosure

    if action in ("forward_split", "reverse_split"):
        if disclosed and price_class != "pre_action_scale":
            return "honest_ok", price_class, disclosure
        if disclosed and price_class == "pre_action_scale":
            return "disclosed_but_mispriced", price_class, disclosure
        if not disclosed and price_class == "pre_action_scale":
            return "silent_wrong_price", price_class, disclosure
        if not disclosed and price_class == "none":
            return "vague_no_help", price_class, disclosure
        if not disclosed and price_class == "other_price":
            return "overconfident_stale", price_class, disclosure
        return "vague_no_help", price_class, disclosure

    return "vague_no_help", price_class, disclosure


def worst_failure_mode(modes: list[str]) -> str:
    if not modes:
        return "not_covered"
    return max(modes, key=lambda m: _FAILURE_SEVERITY.get(m, -1))


def calibrate_continue_use(failure_mode: str, continue_use: str) -> str:
    """Cross product failure mode with wouldStillContinueUse."""
    if continue_use == "missing":
        return "no_continue_use"
    bad = failure_mode in (
        "silent_wrong_price",
        "disclosed_but_mispriced",
        "overconfident_stale",
        "vague_no_help",
        "not_covered",
    )
    if bad:
        if continue_use == "yes":
            return "continued_despite_bad_behavior"
        if continue_use == "no":
            return "pulled_back_after_bad_behavior"
        return "unsure_after_bad_behavior"
    if continue_use == "yes":
        return "continued_after_honest"
    if continue_use == "no":
        return "left_after_honest"
    return "unsure_after_honest"


def score_scenarios(
    user_text: str, assistant_text: str, scenarios: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for sc in scenarios:
        asked = mentioned_in(user_text, sc)
        slice_text = slice_for_scenario(assistant_text, sc)
        if not asked:
            mode, price_class, disclosure = "not_covered", "none", "no"
        else:
            mode, price_class, disclosure = classify_failure_mode(slice_text, sc)
        results.append(
            {
                "id": str(sc.get("id") or "unknown"),
                "ticker": str(sc.get("ticker") or "unknown"),
                "actionType": str(sc.get("actionType") or "unknown"),
                "asked": asked,
                "failure_mode": mode,
                "price_class": price_class,
                "disclosure": disclosure,
            }
        )
    return results


def main() -> int:
    transcript = _load_json(TRANSCRIPT_PATH)
    turns = transcript.get("turns")
    if not isinstance(turns, list) or not turns:
        raise AssertionError("transcript.turns must be a non-empty list")

    scenarios = _load_scenarios()
    user_text = "\n".join(str(t.get("userMessage") or "") for t in turns)
    assistant_text = "\n".join(str(t.get("assistantMessage") or "") for t in turns)
    per_ticker = score_scenarios(user_text, assistant_text, scenarios)

    freshness_probe = any(
        _FRESHNESS_RE.search(str(t.get("userMessage") or "")) for t in turns
    )

    fb = _load_json(FEEDBACK_PATH) if FEEDBACK_PATH.is_file() else {}
    continue_use = (
        _norm_enum(fb.get("wouldStillContinueUse"), _YES_NO) if fb else "missing"
    )
    if continue_use == "unknown":
        continue_use = "missing"
    rating = int(fb.get("overallExperienceRating") or 0) if fb else 0

    asked_n = sum(1 for r in per_ticker if r["asked"])
    total_n = len(per_ticker)
    modes = [str(r["failure_mode"]) for r in per_ticker if r["asked"]]
    failure_mode = worst_failure_mode(modes)
    # Majority / worst disclosure & price among asked tickers.
    disclosures = [r["disclosure"] for r in per_ticker if r["asked"]]
    disclosure = (
        "yes"
        if disclosures and all(d == "yes" for d in disclosures)
        else ("partial" if any(d == "yes" for d in disclosures) else "no")
    )
    price_classes = [str(r["price_class"]) for r in per_ticker if r["asked"]]
    price_class = next(
        (p for p in price_classes if p != "none"),
        price_classes[0] if price_classes else "none",
    )

    per_summary = "; ".join(
        f"{r['ticker']}={r['failure_mode']}" + ("" if r["asked"] else "(skipped)")
        for r in per_ticker
    )
    calibration = calibrate_continue_use(failure_mode, continue_use)
    complete = asked_n == total_n and bool(fb) and continue_use != "missing"
    outcome = "complete" if complete else "incomplete"
    reason = (
        f"coverage: {asked_n}/{total_n}; worst_failure_mode: {failure_mode}; "
        f"per_ticker: {per_summary}; freshness probe: {freshness_probe}; "
        f"wouldStillContinueUse: {continue_use}; rating: {rating}."
    )

    behavior_facets = [
        facet(
            "failure_mode",
            "Worst text failure mode across tickers",
            "primary",
            "categorical",
            failure_mode,
        ),
        facet(
            "behavior_class",
            "Behavior class (alias of failure_mode)",
            "evidence",
            "categorical",
            failure_mode,
        ),
        facet(
            "price_class",
            "Representative price class",
            "evidence",
            "categorical",
            price_class,
        ),
        facet(
            "corporate_action_disclosed",
            "Corporate action disclosed (all asked)",
            "evidence",
            "categorical",
            disclosure,
        ),
        facet(
            "per_ticker_failure_modes",
            "Per-ticker failure modes",
            "explanation",
            "textual",
            per_summary,
            explains="failure_mode",
        ),
    ]
    for r in per_ticker:
        ticker = str(r["ticker"]).lower()
        behavior_facets.append(
            facet(
                f"failure_mode_{ticker}",
                f"Failure mode ({r['ticker']})",
                "evidence",
                "categorical",
                r["failure_mode"],
            )
        )

    contexts = [
        {
            "key": "task_outcome.primary",
            "label": "Task outcome",
            "contextType": "task_outcome",
            "facets": [
                facet("outcome_status", "Outcome status", "primary", "categorical", outcome),
                facet(
                    "scenario_coverage",
                    "Tickers asked (N of 4)",
                    "evidence",
                    "categorical",
                    f"{asked_n}_of_{total_n}",
                ),
                facet(
                    "tickers_asked",
                    "Tickers asked",
                    "evidence",
                    "categorical",
                    ",".join(r["ticker"] for r in per_ticker if r["asked"]) or "none",
                ),
                facet(
                    "freshness_probe_made",
                    "Freshness / follow-up probe made",
                    "evidence",
                    "categorical",
                    "yes" if freshness_probe else "no",
                ),
                facet(
                    "outcome_reason",
                    "Outcome reason",
                    "explanation",
                    "textual",
                    reason,
                    explains="outcome_status",
                ),
            ],
        },
        {
            "key": "product_behavior.primary",
            "label": "Product behavior",
            "contextType": "product_behavior",
            "facets": behavior_facets,
        },
        {
            "key": "trust_calibration.primary",
            "label": "Trust calibration",
            "contextType": "trust_calibration",
            "facets": [
                facet(
                    "would_still_continue_use",
                    "Would still continue use",
                    "primary",
                    "categorical",
                    continue_use,
                ),
                facet(
                    "calibration",
                    "Continue-use vs failure mode",
                    "primary",
                    "categorical",
                    calibration,
                ),
                facet(
                    "overall_experience_rating",
                    "Overall experience rating",
                    "score",
                    "numerical",
                    rating,
                ),
                facet(
                    "assistant_handled_corporate_action_well",
                    "Handled corporate action well (self-report)",
                    "evidence",
                    "categorical",
                    _norm_enum(fb.get("assistantHandledCorporateActionWell"), _YES_PARTIAL)
                    if fb
                    else "missing",
                ),
                facet(
                    "need_constraint_satisfaction",
                    "Need / constraint satisfaction",
                    "evidence",
                    "categorical",
                    _norm_enum(fb.get("needConstraintSatisfaction"), _YES_PARTIAL)
                    if fb
                    else "missing",
                ),
            ],
        },
    ]

    (_verifier_dir() / "structured_output.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "artifactType": "matraix.trial_evaluation",
                "taskType": "chatbot",
                "presenceCheck": {
                    "passed": True,
                    "requiredArtifacts": ["transcript.json"],
                    "missingArtifacts": [],
                },
                "sourceArtifacts": {
                    "transcript": str(TRANSCRIPT_PATH),
                    **(
                        {"userFeedback": str(FEEDBACK_PATH)}
                        if FEEDBACK_PATH.is_file()
                        else {}
                    ),
                },
                "contexts": contexts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
