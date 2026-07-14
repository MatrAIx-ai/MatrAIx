# Package Owner Setup

End-to-end setup for a **new package owner**: the person who builds
collaborator packages, distributes them to labelers, and merges the returned
results. It assumes nothing beyond a repo checkout. For tool-by-tool detail
see [README.md](README.md); for what labelers receive see
[wiki_collab/collab_kit/README.md](wiki_collab/collab_kit/README.md).

## 1. Prerequisites

- A checkout of this repository (all commands below run from the repo root).
- Python 3.10+ and bash. Packaging and merging are stdlib-only and fully
  offline; **no API keys are required** for any owner-side step.
- Only if you export Amazon histories yourself (step 4, option B):
  `pip install huggingface_hub pyarrow` and a Hugging Face account.
- Access to the gated Hugging Face dataset
  [`MatrAIx2026/MatrAIx2026`](https://huggingface.co/datasets/MatrAIx2026/MatrAIx2026):
  request access on the dataset page and wait for manual approval.

## 2. Choose Persistent Locations

```bash
export MATRIX_PACKAGE_CACHE_ROOT=/path/to/persistent/matraix_cache
export MATRIX_PACKAGE_OUT_ROOT=/path/to/persistent/matraix_packages
mkdir -p "${MATRIX_PACKAGE_CACHE_ROOT}" "${MATRIX_PACKAGE_OUT_ROOT}"
```

Both default to `TMPDIR` when unset. Do not leave them there: the cache pair
is your dataset identity and the out root is your assignment ledger, and
neither survives a reboot or temp cleanup in `TMPDIR`.

## 3. Get The Wiki Cache Pair

The Wiki line runs from a two-file SQLite cache; you do **not** need the raw
Wikipedia data to make packages.

**Option A — download from Hugging Face (normal path):**

```bash
hf download MatrAIx2026/MatrAIx2026 \
  wiki/matraix_wiki_profiles_20260601_v1.sqlite \
  wiki/matraix_wiki_profiles_20260601_v1.manifest.json \
  --repo-type dataset --local-dir /tmp/matraix_dl
mv /tmp/matraix_dl/wiki/matraix_wiki_profiles_20260601_v1.* "${MATRIX_PACKAGE_CACHE_ROOT}/"
```

Verify the transfer before first use — the printed hash must equal the
`db_sha256` field inside the manifest:

```bash
sha256sum "${MATRIX_PACKAGE_CACHE_ROOT}/matraix_wiki_profiles_20260601_v1.sqlite"
grep db_sha256 "${MATRIX_PACKAGE_CACHE_ROOT}/matraix_wiki_profiles_20260601_v1.manifest.json"
```

The `.sqlite` and `.manifest.json` are only valid **as a pair** (the manifest
carries the `db_sha256` stamped into every package); `make_package.sh` refuses
to run with the DB present and the manifest missing. See "Sharing The Profile
DB Cache" in [README.md](README.md).

**Option B — rebuild from the clean profile layer** (only if you maintain the
layer yourself): see "Wiki Packages" in [README.md](README.md). Rebuilds are
deterministic and atomic; on the same machine/SQLite version they reproduce
the same `db_sha256`.

## 4. Get The Amazon User Histories (If You Run The Amazon Line)

The Amazon builder slices a normalized `user_histories.jsonl.gz`; the file's
own bytes are its dataset identity (its sha256 is stamped into packages).

- **Option A — take the exact file from the previous owner.** Keeps one
  consistent dataset identity across owners. Verify with `sha256sum` against
  the hash the previous owner gives you.
- **Option B — export your own from Hugging Face** with a reviewer-ID list
  (`huggingface-cli login` first; see "Export From Hugging Face" in
  [README.md](README.md)). A fresh export is a *new* dataset identity — do not
  mix its packages with ranges issued from another owner's file.

## 5. Make A Package

```bash
# Wiki: WIKI_CLEAN_DIR must be set, but is not read while the cache pair
# exists — a placeholder is fine for a downloaded cache.
WIKI_CLEAN_DIR=/unused-placeholder \
persona/existing_data_curation/scripts/make_package.sh 0:100 alice

# Amazon:
persona/existing_data_curation/scripts/make_amazon_package.sh \
  /path/to/user_histories.jsonl.gz 0:100 alice
```

Each run prints the `.tar.gz` to send. It is self-contained: the labeler needs
no repo access, no source data, and no owner cache.

## 6. Distribute And Track Assignments

- **Keep a ledger** (a simple table is enough): range → labeler → sent /
  returned. Assignment IDs encode only the range (`A_0_100`, `AMZ_0_100`);
  nothing stops two owners from issuing the same rows twice, so agree on
  non-overlapping ranges and use a distinct worker id per labeler.
- **Keep every package's out directory** under `MATRIX_PACKAGE_OUT_ROOT` —
  its `package_manifest.json` is required for strict validation when results
  come back.
- What to tell the labeler: unpack the archive, run `./run_assignment.sh`
  (Python 3.10+, plus their own Codex or Claude CLI subscription login), and
  send back `results.jsonl`. Their kit README covers the rest.

## 7. Merge Returned Results

```bash
python3 persona/existing_data_curation/scripts/merge_collab_results.py \
  --results returns/alice.results.jsonl \
  --results returns/bob.results.jsonl \
  --dimensions persona/dimensions.json \
  --db "${MATRIX_PACKAGE_CACHE_ROOT}/matraix_wiki_profiles_20260601_v1.sqlite" \
  --package-manifest "${MATRIX_PACKAGE_OUT_ROOT}/A_0_100_alice/package_manifest.json" \
  --package-manifest "${MATRIX_PACKAGE_OUT_ROOT}/A_100_200_bob/package_manifest.json" \
  --out merged.jsonl.gz --report merge_report.json
```

Pass one `--package-manifest` per `--results` file, in the same order. The
tool checks the collaborator contract, verifies every row against the source
DB and its package manifest, and refuses to write output on blocking errors.

## 8. Handing The Role To The Next Owner

Give them:

1. this repo (or the PR branch) and a pointer to this file;
2. the Wiki cache pair — or simply approval for the gated Hugging Face
   dataset, since the pair lives there;
3. the Amazon `user_histories.jsonl.gz` (exact bytes) plus its sha256, if the
   Amazon line is active;
4. your assignment ledger and the package out directories for everything
   still in flight;
5. nothing else — no raw datasets, no credentials.
