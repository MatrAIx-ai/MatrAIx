# Wiki Persona Attribution Packages

This directory contains the worker package runner for Wikipedia-derived persona
attribution. The owner builds a self-contained package from a profile SQLite DB;
the worker unpacks it, runs inference with their own model access, validates
`results.jsonl`, and sends that file back.

All commands below run from the repository root unless noted.

## Owner: Build A Wiki Package

You need:

- a Wikipedia profile SQLite DB built by
  `persona/curation/existing_data/scripts/build_wiki_profile_db.py`
- the matching dataset id and dataset sha256
- the persona dimensions file, normally `persona/schema/dimensions.json`
- a half-open row range and worker id

Build a package with the unified owner entrypoint:

```bash
python persona/curation/existing_data/scripts/make_package.py \
  --source wiki \
  --db /path/to/personabench-wiki-profiles.sqlite \
  --dimensions persona/schema/dimensions.json \
  --range 0:100 \
  --out-dir /tmp/personabench_packages/A_0_100_alice \
  --assignment-id A_0_100 \
  --worker-id alice \
  --dataset-id personabench_wiki_profiles_v1 \
  --dataset-sha256 DATASET_SHA256 \
  --force
```

The output directory contains:

- `tasks.jsonl`: one Wikipedia profile per row
- `dimensions.json`: dimensions and allowed values for this assignment
- `assignment.json`: range, worker, dataset, and checksum metadata
- `package_manifest.json`: immutable-file checksums
- `run_assignment.sh`: worker entrypoint
- `collab_kit/`: inference runner, backend adapters, schemas, and validator
- `<out-dir>.tar.gz`: archive to send to the worker

Send the `.tar.gz` archive. Keep the unpacked output directory because its
`package_manifest.json` is useful when validating returned results.

## Worker: Run Inference

Unpack the archive and work inside the package directory:

```bash
tar -xzf A_0_100_alice.tar.gz
cd A_0_100_alice
./run_assignment.sh --status
```

The package runner supports three real backends:

| Backend | Model | Worker requirement |
|---|---|---|
| `codex-acp` | `gpt-5.5` | logged-in Codex CLI |
| `claude-code-acp` | `claude-opus-4-8` | logged-in Claude Code CLI |
| `qwen-local` | `Qwen/Qwen3.6-35B-A3B` | local OpenAI-compatible Qwen server |

The interactive TUI is:

```bash
./run_assignment.sh
```

Use:

1. `Environment check`
2. `Configure backend/model/effort`
3. `Real run / resume`
4. `Validate results`

The run is resumable. Progress is checkpointed to
`results.jsonl.progress.jsonl`; rerunning skips completed `(profile, category)`
units.

### Codex Or Claude

```bash
./run_assignment.sh --backend codex-acp --effort high --jobs 4 --yes --run
./run_assignment.sh --validate
```

or:

```bash
./run_assignment.sh --backend claude-code-acp --effort high --jobs 4 --yes --run
./run_assignment.sh --validate
```

### Local Qwen With vLLM

Use vLLM when you want to keep one or more GPUs saturated. Install it in a
separate environment on the worker machine:

```bash
python3 -m venv /tmp/qwen_vllm_venv
/tmp/qwen_vllm_venv/bin/python -m pip install --upgrade pip
/tmp/qwen_vllm_venv/bin/python -m pip install -U vllm
```

Start the OpenAI-compatible server. Set `--tensor-parallel-size` to the number
of GPUs you want this model to use:

```bash
PATH=/tmp/qwen_vllm_venv/bin:$PATH \
HF_HOME=/path/to/hf_cache \
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
/tmp/qwen_vllm_venv/bin/vllm serve Qwen/Qwen3.6-35B-A3B \
  --host 127.0.0.1 \
  --port 8001 \
  --tensor-parallel-size 8 \
  --served-model-name Qwen/Qwen3.6-35B-A3B \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.95 \
  --trust-remote-code \
  --reasoning-parser qwen3 \
  --default-chat-template-kwargs '{"enable_thinking": false}'
```

Run inference from a second terminal in the package directory:

```bash
export QWEN_BASE_URL=http://127.0.0.1:8001/v1
export QWEN_API_KEY=EMPTY
export WIKI_COLLAB_QWEN_RESPONSE_FORMAT=1
export WIKI_COLLAB_QWEN_MAX_TOKENS=2048

./run_assignment.sh --backend qwen-local \
  --model Qwen/Qwen3.6-35B-A3B \
  --jobs 24 \
  --yes --run
./run_assignment.sh --validate
```

Tune `--jobs` for the machine. A practical pattern is to start at 8, watch
`nvidia-smi`, and increase to 16 or 24 if GPU utilization is below target and
the server has no OOM/HTTP errors. The runner is resumable, so stopping with
Ctrl-C and rerunning with a different `--jobs` value is safe.

### Local Qwen With Transformers Host

Install model dependencies in the worker environment first. Exact install
commands depend on the machine, CUDA version, and package manager, but the host
requires `torch` and `transformers`; `accelerate` is usually needed for
`device_map=auto`.

Start the bundled host in one terminal:

```bash
python collab_kit/qwen_transformers_host.py \
  --model Qwen/Qwen3.6-35B-A3B \
  --host 127.0.0.1 \
  --port 8000
```

Run inference from a second terminal in the same package directory:

```bash
export QWEN_BASE_URL=http://127.0.0.1:8000/v1
export QWEN_API_KEY=EMPTY

./run_assignment.sh --backend qwen-local --jobs 1 --yes --run
./run_assignment.sh --validate
```

`qwen-local` uses the same runner contract as Codex/Claude. The adapter calls
the local host's `/v1/chat/completions`, extracts the final JSON object, writes
checkpointed progress, then runs the same final conformance validator.

Qwen may have a shorter usable context window than hosted models. The Qwen path
therefore uses a compact prompt and sends the first 24000 visible characters of
`profile_text` by default. Override this when needed:

```bash
export WIKI_COLLAB_PROFILE_TEXT_CHAR_LIMIT=16000  # tighter context budget
export WIKI_COLLAB_PROFILE_TEXT_CHAR_LIMIT=0      # disable truncation
```

If your local model is served under a different model id, pass an alias:

```bash
./run_assignment.sh --backend qwen-local --model local-qwen --jobs 1 --yes --run
```

## Validate And Return

Always run:

```bash
./run_assignment.sh --validate
```

Return `results.jsonl` only unless the owner asks for logs. If inference failed
and cannot be resumed locally, also send `results.jsonl.failures.jsonl`; it
contains per-unit backend errors.
