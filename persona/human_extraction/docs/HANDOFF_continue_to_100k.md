# Handoff — Continue Amazon 100K persona extraction to completion

**You are picking up the Amazon 100K persona extraction (`MatrAIx2026/MatrAIx2026`).**
A prior operator reached **38.2% (38,219 unique users)** and spent their compute budget.
Your job: extract the remaining **61,781 users**, upload to Hugging Face as a PR, and
coordinate the merge.

This brief is **self-contained**. It supersedes the older `AMAZON_EXTRACTION_HANDOFF.md`
(which describes a stalled 2026-07-06 attempt that produced no output); read that only for
the sharding mechanics.

---

## 0. Environment assumptions — read first

The reference run used a batch-scheduled HPC cluster with **NVIDIA H100 and A100 GPUs**.
**Do not assume you have the same system.** Two layers:

- **Portable — the dataset contract (must hold on ANY system):** same model
  `Qwen/Qwen3.6-35B-A3B`, `PROMPT_VARIANT=medium_b`, the **schema validation** step
  (enforces schema before writing), the shared **selection index**
  (`selected_users_100k.parquet`, one fixed hex home bucket `00`–`ff` per user),
  **resume-skip by `user_id`**, the **remaining-bucket list** in §2, and **upload as an HF
  PR** (contributors are read-only on the org). Honor these and your output merges cleanly
  with the existing 38K.
- **Not portable (translate to your stack):** scheduler/queue mechanics and node/GPU
  layout. The reference run's config and GPU hours are in #265; its scheduler scripts
  are available on request but are **not required**.

## 1. What is already done (do NOT re-extract)

| Tranche | GPU | Precision / parallelism | Buckets | Unique users |
|---|---|---|---|---:|
| A | NVIDIA H100 80GB | FP8, TP=1 (1 model/GPU) | 63 (≤ 0x3f) | 22,795 |
| B | NVIDIA A100 40GB | BF16, TP=4 (1 model/4-GPU node) | 40 (0x40–0x67) | 15,424 |
| **Total** | | | **103** | **38,219** |

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

## 3. Compute

GPU hours and GPU types for the reference run are reported separately in **#265**.
That run produced the 38,219 users in §1; the remaining 61,781 in §2 are unextracted.
Measure on your own hardware before committing an allocation.

## 4. Prerequisites

1. **Your own GPU compute** (the prior allocation is spent; see #265).
2. **An HF write-role token** that can open PRs on `MatrAIx2026/MatrAIx2026`. All uploads go
   as **PRs, not direct pushes** (contributors are read-only on the org).
3. **The runner — NOTE: the required changes are NOT yet on `main`.**
   `persona/human_extraction/scripts/run_extraction_amazon.py` on `main` does **not** have
   the `medium_b` prompt variant, the schema validation step, or portable paths. They are
   split across two open PRs, and you need **both**:

   | Piece | PR | State |
   |---|---|---|
   | Portable paths + schema validation | **#174** | open |
   | `medium_b` prompt variant | **#264** | open |

   **Land or check out both before extracting.** Running `main`'s runner as-is uses a
   different prompt with no schema validation, which will **not** match the existing 38K and
   forks the dataset. Until they merge, check them out with:
   ```bash
   gh pr checkout 174 && gh pr checkout 264   # or merge both into your working branch
   ```
4. **The selection index — download the exact file; do NOT regenerate it.**
   `selected_users_100k.parquet` is git-ignored, so the authoritative copy — the one that
   produced the 38,219 rows — is published on **HF PR #53** at
   `amazon/extraction_v1/qwen36/final_20260715/selected_users_100k.parquet`
   (100,000 rows / 100,000 unique `user_id` / 256 buckets), with its hash alongside in
   `selected_users_100k.sha256`:
   ```
   sha256  8a0084628f32a06f8f823126f819ef1abcc8387978b44f79eb4f923cb5e8ce12
   bytes   3457804
   ```
   ```bash
   huggingface-cli download MatrAIx2026/MatrAIx2026 --repo-type dataset \
     --revision refs/pr/53 \
     --include 'amazon/extraction_v1/qwen36/final_20260715/selected_users_100k*' \
     --local-dir ./sel
   sha256sum ./sel/amazon/extraction_v1/qwen36/final_20260715/selected_users_100k.parquet
   ```
   **Regenerating the index is NOT reliable.** An earlier version of this brief suggested
   regenerating it via `explore_amazon_data.ipynb` (`SEED=20260705`); a second operator did
   so and got **different per-bucket counts** (bucket 10: 394 vs 403; bucket 47: 398 vs 372).
   A mismatched index silently diverges the `user_id` sets and corrupts both coverage
   bookkeeping and the merged dataset. Verify the SHA-256 before extracting anything.
5. **HF access** to the gated source dataset (`HF_TOKEN` with access granted).

## 5. Hard rules

1. **No duplicate extraction.** Keep a **separate output dir per concurrent worker** and
   **disjoint bucket ranges**. Resume-skip only dedups *within one* output dir.
2. **Fixed config for dataset consistency:** model `Qwen/Qwen3.6-35B-A3B`,
   `PROMPT_VARIANT=medium_b`, schema validation on. Changing the prompt or model forks the
   dataset and breaks the merge with the existing 38K.
3. **Never launch large compute jobs without the owner's explicit go-ahead.**

## 6. Recommended plan

1. **Land/checkout runner PRs #174 and #264** (§4.3) and **download** the exact selection index, verifying its SHA-256 (§4.4 — do not regenerate it).
2. **Seed resume for the 14 partials:** download those buckets' shards from HF PR #53 into
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
3. **Run untouched buckets** (`30`, `68`–`ff`) in your output dir — no overlap with the 38K.
4. Drive the runner per bucket with `PROMPT_VARIANT=medium_b`, the selection parquet, and
   your output dir. Scale concurrency to your scheduler; keep dirs/ranges disjoint (rule 1).

## 7. Upload + merge

1. Upload your output as a review **PR** to `MatrAIx2026/MatrAIx2026` (dedup per shard by
   `user_id`; include a manifest with per-bucket `rows_unique` / `selected` / `state`).
2. Coordinate the merge of your PR **and** PR #53 into the dataset's main branch with the
   team maintainers (contributors cannot self-merge).

## 8. Definition of done

- All 256 buckets complete (every bucket `rows_unique ≥ selected`), 100,000 unique users,
  zero cross-dir overlap.
- Full dataset uploaded to HF and merged into the dataset's main branch.

---

### Pointers
- Runner: `persona/human_extraction/scripts/run_extraction_amazon.py` (**plus open PRs #174
  and #264 — both required, see §4.3**)
- Remaining-bucket report: `persona/human_extraction/scripts/report_remaining_buckets.py`
- Sharding mechanics (older, partly stale): `persona/human_extraction/AMAZON_EXTRACTION_HANDOFF.md`
- Schema: `persona/schema/dimensions.json`
- Done dataset: HF `MatrAIx2026/MatrAIx2026` PR #53, `amazon/extraction_v1/qwen36/final_20260715/`
