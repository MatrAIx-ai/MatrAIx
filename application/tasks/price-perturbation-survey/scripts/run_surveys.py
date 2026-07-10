#!/usr/bin/env python3
"""Collect responses to the generated surveys.

Reads a surveys JSONL (from generate_surveys.py), sends each survey's
``prompt`` to a model, parses/validates the 6-field response with the
task's own collector, and appends one result line per survey to a
checkpointed output JSONL — resumable, so a rerun continues where it
left off.

Model-agnostic by design. Two backends:

* ``--dry-run`` (default): no model is called at all. Each prompt is
  validated against a canned valid response — a fast preflight that
  confirms every survey renders and every result row is well-formed.
  This is the safe default; it never spins up a heavy local process.
* ``--endpoint URL``: POSTs to any OpenAI-compatible
  ``/v1/chat/completions`` endpoint (a hosted API, or a local server
  like LM Studio / vLLM). Bring your own model and key — set the key in
  ``$SURVEY_API_KEY``. Nothing about the survey format is provider-
  specific, so whatever the team standardizes on plugs in here.

Persona-optional: pass ``--persona-prompt-file`` to prepend a persona
system prompt (the survey then reads as "you, this persona, react to
this change"); omit it for a bare, persona-less survey. Either way the
response contract is identical.

Usage:
    # preflight — validate all surveys, no model (safe, instant)
    python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
        --out output/preflight.jsonl --dry-run

    # real collection against an OpenAI-compatible endpoint
    export SURVEY_API_KEY=sk-...
    python3 scripts/run_surveys.py --surveys fixtures/surveys_v1.jsonl \
        --out output/survey_responses.jsonl \
        --endpoint https://api.example.com/v1/chat/completions \
        --model some-model-id
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

_TASK_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TASK_DIR))
from pipeline.collector import parse_decision  # noqa: E402

_CANNED_DRY_RUN = json.dumps({
    "purchase_intent": "might_or_might_not",
    "price_fairness": "about_right",
    "alternative_seeking": "no",
    "purchase_timing": "buy_now",
    "necessity_level": "nice_to_have",
    "reasoning": "Dry-run canned response.",
})


def _call_endpoint(
    endpoint: str,
    prompt: str,
    system: str | None,
    model: str,
    timeout: float,
) -> str:
    """POST to an OpenAI-compatible chat-completions endpoint."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("SURVEY_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = requests.post(
        endpoint,
        headers=headers,
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 400,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _load_done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        json.loads(line)["survey_id"]
        for line in path.read_text().splitlines()
        if line.strip()
    }


def run(
    surveys_path: Path,
    out_path: Path,
    *,
    endpoint: str | None,
    model: str,
    limit: int | None,
    system_prompt: str | None,
    delay: float,
    timeout: float,
) -> None:
    surveys = [
        json.loads(line)
        for line in surveys_path.read_text().splitlines()
        if line.strip()
    ]
    if limit:
        surveys = surveys[:limit]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _load_done_ids(out_path)
    todo = [s for s in surveys if s["survey_id"] not in done]
    mode = f"endpoint {endpoint}" if endpoint else "dry-run (no model)"
    print(f"{len(surveys)} surveys, {len(done)} already done, "
          f"{len(todo)} to run [{mode}]", flush=True)

    ok = failed = 0
    for i, survey in enumerate(todo):
        if i > 0 and endpoint:
            time.sleep(delay)
        try:
            if endpoint:
                raw = _call_endpoint(
                    endpoint, survey["prompt"], system_prompt, model, timeout
                )
            else:
                raw = _CANNED_DRY_RUN
            parsed = parse_decision(raw)
            result = {
                "survey_id": survey["survey_id"],
                "asin": survey["asin"],
                "perturbation": survey["perturbation"],
                "purchase_intent": parsed.purchase_intent,
                "price_fairness": parsed.price_fairness,
                "alternative_seeking": parsed.alternative_seeking,
                "purchase_timing": parsed.purchase_timing,
                "necessity_level": parsed.necessity_level,
                "would_buy": parsed.would_buy,
                "reasoning": parsed.reasoning,
            }
            with out_path.open("a") as f:
                f.write(json.dumps(result) + "\n")
            ok += 1
        except Exception as e:  # noqa: BLE001 — log and continue
            failed += 1
            with out_path.with_suffix(".errors.jsonl").open("a") as f:
                f.write(json.dumps({
                    "survey_id": survey["survey_id"],
                    "error": f"{type(e).__name__}: {e}",
                }) + "\n")
        if (ok + failed) % 25 == 0:
            print(f"  {ok + failed}/{len(todo)} (ok={ok} failed={failed})",
                  flush=True)

    print(f"done: {ok} ok, {failed} failed -> {out_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surveys", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--endpoint", default=None,
        help="OpenAI-compatible /v1/chat/completions URL. Omit for dry-run.",
    )
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--persona-prompt-file", type=Path, default=None)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Explicit no-model preflight (same as omitting --endpoint).",
    )
    args = parser.parse_args()

    endpoint = None if args.dry_run else args.endpoint
    system_prompt = (
        args.persona_prompt_file.read_text()
        if args.persona_prompt_file else None
    )
    run(
        args.surveys,
        args.out,
        endpoint=endpoint,
        model=args.model,
        limit=args.limit,
        system_prompt=system_prompt,
        delay=args.delay,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
