---
name: persona-extraction-quality-check
description: 'Score one extracted persona against its source profile with the canonical EXTRACTION_QUALITY_RUBRIC.md. Use for one-persona M1-M7 extraction quality checks on Stack Overflow, Wikipedia, Amazon, or other sources.'
argument-hint: 'persona=<path-to-one-persona> output=<path-to-result.json>'
user-invocable: true
disable-model-invocation: false
---

# Persona Extraction Quality Check

Score exactly **one persona** at a time.

## Input

The user provides:

1. `persona`: one self-contained persona containing:
   - the complete source profile, and
   - the complete extracted fields (`field_id`, `value`, `evidence`, `description` when present, `assignment_type`, and `confidence`);
2. `output`: the path where the result JSON must be written.

If the source profile or extracted fields are missing, stop and ask for them. Never guess the matching source record.

## Context

Read the complete canonical rubric before scoring:

`persona/human_extraction/docs/EXTRACTION_QUALITY_RUBRIC.md`

Use its M1–M7 definitions and 1–5 anchors exactly. Do not create a different scale.

## Task

1. Read the entire source profile and all extracted fields.
2. Check every extracted field for:
   - M1 value accuracy,
   - M2 evidence grounding,
   - M3 description faithfulness.
3. Judge the complete persona for:
   - M4 no over-claiming,
   - M5 coverage,
   - M6 internal consistency,
   - M7 overall fidelity.
4. Write exactly one JSON object to `output`.

The source profile is ground truth. Do not treat extraction confidence as proof of correctness. Use `"n/a"` for M3 only when the extraction has no description field.

## Output

```json
{
  "persona_id": "<stable ID from the input>",
  "M1_value": {"score": 1, "reason": "<short reason citing fields/source>"},
  "M2_evidence": {"score": 1, "reason": "<short reason citing fields/source>"},
  "M3_description": {"score": "n/a", "reason": "no description field"},
  "M4_overclaim": {"score": 1, "reason": "<short reason citing fields/source>"},
  "M5_coverage": {"score": 1, "reason": "<short reason citing fields/source>"},
  "M6_consistency": {"score": 1, "reason": "<short reason citing fields/source>"},
  "M7_overall": {"score": 1, "reason": "<short reason citing fields/source>"}
}
```

Every applicable score must be an integer from 1 through 5, and every reason must cite concrete evidence from this persona.

Batch selection, source/extraction pairing, parallel model calls, agreement analysis, and aggregate statistics are outside this skill. Handle them with the caller or separate Python scripts.
