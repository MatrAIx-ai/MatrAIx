# Persona Extraction — Extraction-Quality Rating

**Unit: score one persona at a time.** Read the source profile + the extracted fields, then give
**1–5** on each metric. **Work top to bottom:**

1. **Step 1 — quality of what it extracted** (go field by field): M1 value → M2 evidence → M3 description
2. **Step 2 — did it extract the right set** (whole persona): M4 over-claim → M5 coverage
3. **Step 3 — coherence & gut check**: M6 consistency → M7 overall

**1–5 scale:** 5 = no problem, 4 = minor issue, 3 = moderate issue, 2 = major issue, 1 = completely
wrong. (Tables define 5 / 3 / 1; 4 and 2 fall in between.)

## Step 1 — quality of what it extracted (look at each field)

| # | Metric | **5 (good)** | **3 (mixed)** | **1 (bad)** |
|---|---|---|---|---|
| **M1** | **Value accuracy** — for attributes the profile supports, is the `value` right? | almost all right | several wrong buckets | many contradict the profile |
| **M2** | **Evidence grounding** — is `evidence` a real quote that supports the value? | quotes in the profile and support the value | mostly grounded, some weak / fabricated | often missing, fabricated, or mismatched |
| **M3** | **Description faithfulness** — does `description` invent or exaggerate? | concrete, accurate, traceable | some vague / mild exaggeration | fabricates detail or contradicts the profile |

## Step 2 — did it extract the right set (step back to the whole persona)

| # | Metric | **5 (good)** | **3 (mixed)** | **1 (bad)** |
|---|---|---|---|---|
| **M4** | **No over-claiming** — did it assign values to attributes the profile does *not* support? | nothing invented; unsupported → null | a few over-claims on thin evidence | many hallucinated attributes |
| **M5** | **Coverage** — did it miss attributes the profile clearly states? | almost everything captured | got the obvious, missed some | misses a lot |

## Step 3 — coherence & gut check

| # | Metric | **5 (good)** | **3 (mixed)** | **1 (bad)** |
|---|---|---|---|---|
| **M6** | **Internal consistency** — do the fields contradict each other? (age ↔ generation ↔ life_stage, job ↔ region…) | fully coherent | one or two mild tensions | fields clearly contradict |
| **M7** | **Overall fidelity** — overall, could you faithfully role-play this person from it? | faithful, usable as-is | broadly right, several misleading errors | seriously distorted, not this person |

> Each metric looks at a **different part** of the record (M1–M3 = the value / evidence / description
> fields; M4–M5 = the *set* of attributes; M6 = across fields; M7 = the whole). M7 is a deliberate
> gut-check summary, so it will correlate with the rest. To swap M7 for something more independent, use
> **Assignment-type correctness** (is `direct / summary_inference / unsupported` labeled right?).

## Worked example (a real extracted record — `global_idx` 0, `qid` Q91 "Abraham Lincoln")

**Source profile** (this is your ground truth — everything is judged against it):

> Abraham Lincoln (February 12, 1809 – April 15, 1865) was the 16th president of the United States,
> serving from 1861 until his assassination in 1865. Born into poverty in a one-room log cabin in
> Kentucky, he became a lawyer and Whig Party leader, led the Union through the Civil War, and
> abolished slavery with the Emancipation Proclamation.

**Extracted fields** (the **actual** extraction output — nothing invented for this example):

| field_id | value | evidence | assignment_type | conf |
|---|---|---|---|:--:|
| age_bracket | 55–64 | (February 12, 1809 - April 15, 1865) | structured_claim | 0.40 |
| region | North America | the 16th president of the United States | structured_claim | 0.96 |
| gender_identity | Man | He led the United States | direct | 0.95 |
| urbanicity | Rural | Born in a one-room log cabin in Kentucky | summary_inference | 0.45 |
| demo_marital_status | *(null)* | *(empty)* | unsupported | 0.00 |

**Scores.** This record is a clean extraction, so most metrics are 5 — scored honestly, one line each.
(For what a 3 or a 1 looks like, use the 5 / 3 / 1 anchors in the metric tables above.)

| metric | score | note |
|---|:--:|---|
| M1 Value accuracy | 5 | every value matches the profile |
| M2 Evidence grounding | 5 | each quote is taken verbatim from the profile |
| M3 Description faithfulness | n/a | this older record has no `description` field (the full Qwen output does) |
| M4 No over-claiming | 5 | nothing invented; `demo_marital_status` is correctly left null / unsupported |
| M5 Coverage | n/a | can't judge from the 5 fields shown — score it on the full ~1,290-field record |
| M6 Internal consistency | 5 | all fields fit one coherent person |
| M7 Overall fidelity | 5 | faithful and fully grounded, no hallucination |
