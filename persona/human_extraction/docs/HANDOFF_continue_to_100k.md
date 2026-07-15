# Handoff — Continue Amazon 100K persona extraction to completion

**You are picking up the Amazon 100K persona extraction (`MatrAIx2026/MatrAIx2026`).**
A prior operator reached **38.2% (38,219 unique users)** and spent their compute budget.
Your job: extract the remaining **61,781 users**, upload to Hugging Face as a PR, and
coordinate the merge.

This brief is **self-contained** — it does not depend on any private operator repo. It
supersedes the older `AMAZON_EXTRACTION_HANDOFF.md` (which describes a stalled 2026-07-06
Slurm attempt that produced no output); read that only for the sharding mechanics.

---

## 0. Environment assumptions — read first

The prior run used a specific HPC (NCAR Casper + Derecho, PBS scheduler). **Do not assume
you have the same system.** Two layers:

- **Portable — the dataset contract (must hold on ANY system):** same model
  `Qwen/Qwen3.6-35B-A3B`, `PROMPT_VARIANT=medium_b`, the schema **sanitizer** (enforces
  schema before writing; upstream PR #174), the shared **selection index**
  (`selected_users_100k.parquet`, one fixed hex home bucket `00`–`ff` per user),
  **resume-skip by `user_id`**, the **remaining-bucket list** in §2, and **upload as an HF
  PR** (contributors are read-only on the org). Honor these and your output merges cleanly
  with the existing 38K.
- **Not portable (translate to your stack):** scheduler/queue mechanics, node/GPU layout
  (e.g. tensor-parallel degree), and throughput/cost numbers. The prior operator's PBS
  scripts and measured NCAR throughput are available on request but are **not required** —
  reuse the runner + dataset contract and plug in your own scheduling.

## 1. What is already done (do NOT re-extract)

| System (prior run) | Buckets | Unique users |
|---|---|---:|
| H100 (fp8, tp=1) | 63 (≤ 0x3f) | 22,795 |
| A100 (bf16, tp=4) | 40 (0x40–0x67) | 15,424 |
| **Total** | **103** | **38,219** |

- 89 buckets complete, 14 partial, zero cross-tranche overlap.
- The done dataset is on HF as **PR #53**, path
  `amazon/extraction_v1/qwen36/final_20260715/` (both tranches + `manifest.json`, deduped
  by `user_id`). **This is your ground truth for what's covered** — pull from here.
  The manifest lists per-bucket `rows_unique` / `selected` / `state`.

## 2. What remains — 61,781 users

**14 partial buckets** (top-up; `have/selected`):
`0f 368/372, 10 240/403, 13 216/405, 16 208/367, 1e 360/382, 22 72/400, 29 344/409,
2f 264/381, 32 280/395, 36 256/411, 3d 184/395, 3f 192/373, 47 306/372, 4d 259/401`

**153 untouched buckets:** `30`, then all of `68`–`ff`.

Regenerate this breakdown anytime (needs pyarrow):
```bash
python persona/human_extraction/scripts/report_remaining_buckets.py
```

## 3. Prerequisites

1. **Your own GPU compute** sized for ~61,781 extractions (the prior allocation is spent).
2. **An HF write-role token** that can open PRs on `MatrAIx2026/MatrAIx2026`. All uploads go
   as **PRs, not direct pushes** (contributors are read-only on the org).
3. **The runner** (already on `main`):
   `persona/human_extraction/scripts/run_extraction_amazon.py` — resume-safe (skips
   `user_id`s already in the output dir), writes `prompt_variant`, default `medium_b`,
   includes the schema sanitizer.

## 4. Hard rules

1. **No duplicate extraction.** Keep a **separate output dir per concurrent worker** and
   **disjoint bucket ranges**. Resume-skip only dedups *within one* output dir.
2. **Fixed config for dataset consistency:** model `Qwen/Qwen3.6-35B-A3B`,
   `PROMPT_VARIANT=medium_b`, the schema sanitizer. Changing the prompt or model forks the
   dataset and breaks the merge with the existing 38K.
3. **Never launch large compute jobs without the owner's explicit go-ahead.**

## 5. Recommended plan

1. **Seed resume for the 14 partials:** download those buckets' shards from HF PR #53 into
   your output dir first, so the runner skips their already-done users:
   ```bash
   huggingface-cli download MatrAIx2026/MatrAIx2026 --repo-type dataset \
     --revision refs/pr/53 \
     --include 'amazon/extraction_v1/qwen36/final_20260715/*/shard_{0f,10,13,16,1e,22,29,2f,32,36,3d,3f,47,4d}.jsonl' \
     --local-dir ./seed
   # place each seed/**/shard_XX.jsonl into your OUT_DIR as shard_XX.jsonl before that bucket runs
   ```
   (Or re-run the 14 partials fully in a fresh dir and dedup at final merge — ~2,800 extra
   extractions, simpler.)
2. **Run untouched buckets** (`30`, `68`–`ff`) in your output dir — no overlap with the 38K.
3. Drive the runner per bucket with `PROMPT_VARIANT=medium_b`, the selection parquet, and
   your output dir. Scale concurrency to your scheduler; keep dirs/ranges disjoint (rule 1).

## 6. Upload + merge

1. Upload your output as a review **PR** to `MatrAIx2026/MatrAIx2026` (dedup per shard by
   `user_id`; include a manifest with per-bucket `rows_unique` / `selected` / `state`).
2. Coordinate the merge of your PR **and** PR #53 into the dataset's main branch with the
   team maintainers (contributors cannot self-merge).

## 7. Definition of done

- All 256 buckets complete (every bucket `rows_unique ≥ selected`), 100,000 unique users,
  zero cross-dir overlap.
- Full dataset uploaded to HF and merged into the dataset's main branch.

---

### Pointers
- Runner: `persona/human_extraction/scripts/run_extraction_amazon.py`
- Remaining-bucket report: `persona/human_extraction/scripts/report_remaining_buckets.py`
- Sharding mechanics (older, partly stale): `persona/human_extraction/AMAZON_EXTRACTION_HANDOFF.md`
- Schema: `persona/schema/dimensions.json`
- Done dataset: HF `MatrAIx2026/MatrAIx2026` PR #53, `amazon/extraction_v1/qwen36/final_20260715/`
