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
  layout. §3 gives the exact configs and measured throughput so you can size your own
  compute; the reference scheduler scripts are available on request but are **not
  required**.

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

## 3. Reference run — compute profile & methodology

All numbers below are **measured on the reference run**, not vendor claims. GPU-hours are
**derived from measured throughput × users produced** (not billing records), so treat them
as ±10% planning figures.

### 3.1 Model & serving stack
- Model `Qwen/Qwen3.6-35B-A3B` — MoE, **35B total / ~3B activated**, hybrid
  (Mamba/GatedDeltaNet + attention) blocks, native context 262,144. BF16 weights ≈ **70 GB**.
- Serving: **vLLM ≥ 0.24.0** (needs the `qwen3_5_moe` architecture), torch 2.11, CUDA 12.8/12.9.
- Sampling is greedy (temp=0).

### 3.2 Per-tranche configuration and cost

| | Tranche A | Tranche B |
|---|---|---|
| GPU | **NVIDIA H100 80GB (HBM3)** | **NVIDIA A100 40GB (SXM4)** |
| Precision | FP8 (native Hopper FP8) | BF16 |
| Parallelism | **TP=1**, one model per GPU | **TP=4**, one model per 4-GPU node (160 GB) |
| Batch knobs | `MAX_NUM_SEQS=16`, `BATCH_PROFILES=8`, `MAX_MODEL_LEN=32768` | `max_num_seqs=24` |
| **Measured throughput** | **52.6 users / GPU-hour** | **≈16 users / GPU-hour ≈ 63 users / node-hour** |
| Users produced | 22,795 | 15,424 |
| **Approx. compute consumed** | **≈ 433 H100-GPU-hours** | **≈ 245 node-hours ≈ 980 A100-GPU-hours** |
| Time per ~390-user bucket | ≈ 7.4 h on 1 GPU | ≈ 6 h on one 4-GPU node |

**Total ≈ 433 H100-GPU-hours + ≈ 980 A100-GPU-hours (≈ 1,413 GPU-hours) for 38,219 users.**

**H100 + FP8 is by far the most efficient per GPU-hour** (52.6 vs ≈16 users/GPU-hr). Hopper's
native FP8 gives both the speed and near-BF16 quality, and a 1-GPU task schedules more
easily than a multi-GPU one. If you have H100s, prefer them.

### 3.3 The key parallelism finding (worth reading before you size anything)

On **40 GB** A100s the 35B hybrid model barely fits at TP=2, and the trap is the KV cache:

- **2×(TP=2), two models per 4-GPU node:** leaves only **0.81 GiB for KV = 68,985 tokens
  ≈ 2.11× concurrency** → **KV-starved**; raising `max_num_seqs` above ~4 does nothing.
  Real yield **~20–26 users/node-hour**, and a full ~390-user bucket needed ~20 h, so a 12 h
  walltime **truncated buckets at ~30%** and forced resume passes.
- **TP=4, one model per node:** the model spreads over **160 GB** → **1,607,056 KV tokens
  ≈ 49× concurrency** → **≈63 users/node-hour**, and a full bucket finishes in **~6 h < 12 h**
  → **no truncation, no resume passes**. That is **~2.5–3× more users per node-hour.**
- **Quality is equivalent:** TP=4 vs TP=2 mean supported dims/user **24.2 vs 22.3**, no
  systematic shift. Per-user divergence is inherent temp=0 greedy instability — same
  magnitude as the accepted FP8-vs-BF16 variance.

**Takeaway:** on 40 GB cards, do **not** pack two TP=2 models per node; use TP=4. On 80 GB
cards (H100), TP=1 + FP8 is best. Always check KV-cache headroom before trusting a
`max_num_seqs` setting.

### 3.4 Extraction methodology
1. **Sharding:** 256 hex buckets `00`–`ff`; every user has one fixed home bucket in the
   selection index. One job = one bucket. Disjoint buckets across workers ⇒ no duplicates.
2. **Per user:** read the bucket's selection rows → download that bucket's raw reviews from
   the gated HF dataset → assemble the user's full review history into one `profile_text` →
   run the `medium_b` prompt over the dimension chunks → append one JSON line per user.
3. **Schema validation before write** — rejects over-filled/hallucinated field IDs, invalid
   enum values, and duplicate fields. Without it, early output failed review.
4. **Resume-skip by `user_id`** within an output dir; re-running a bucket tops it up.
5. **Dedup:** a resumed bucket can re-append `user_id`s already present. Dedup per shard by
   `user_id` (keep first) before upload — the reference run had 38,391 raw rows → 38,219
   unique.
6. **Complete vs partial** is derived by comparing a shard's **unique** `user_id` count to
   that bucket's selected count (see `report_remaining_buckets.py`).

### 3.5 Output characteristic (so you don't misread it as failure)
Against the 1,290-dimension schema, a typical user supports only **~25 dimensions
(median ~20)** — most dimensions simply aren't evidenced by one person's reviews. A low
supported-dimension count per user is expected, not a bug.

### 3.6 Sizing the remaining 61,781 users
- **H100, FP8, TP=1:** ≈ **1,175 H100-GPU-hours**.
- **A100 40GB, BF16, TP=4:** ≈ **981 node-hours ≈ 3,924 A100-GPU-hours**.
- Mix to taste; re-measure on your hardware before committing a large allocation.

## 4. Prerequisites

1. **Your own GPU compute**, sized per §3.6 (the prior allocation is spent).
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
4. **The selection index** `persona/human_extraction/data/amazon/selected_users_100k.parquet`
   is **git-ignored**. Obtain a copy, or regenerate it deterministically via
   `persona/human_extraction/notebooks/explore_amazon_data.ipynb` (`SEED=20260705`). It must
   match the reference run's bucket assignment, or coverage bookkeeping breaks.
5. **HF access** to the gated source dataset (`HF_TOKEN` with access granted).

## 5. Hard rules

1. **No duplicate extraction.** Keep a **separate output dir per concurrent worker** and
   **disjoint bucket ranges**. Resume-skip only dedups *within one* output dir.
2. **Fixed config for dataset consistency:** model `Qwen/Qwen3.6-35B-A3B`,
   `PROMPT_VARIANT=medium_b`, schema validation on. Changing the prompt or model forks the
   dataset and breaks the merge with the existing 38K.
3. **Never launch large compute jobs without the owner's explicit go-ahead.**

## 6. Recommended plan

1. **Land/checkout runner PRs #174 and #264** (§4.3) and obtain the selection index (§4.4).
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
