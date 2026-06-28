# OASIS Multi-Agent Docker Cluster on Greenland

A **real** containerized run of the OASIS social simulation on the Greenland SDB
pod: every social-media user is an LLM-backed agent in its **own Docker
container** (carrying its own vLLM "brain"), and a single **orchestrator
container** spawns and manages them all.

```
                         pod host (p4d.24xlarge, 8x A100)
  ┌────────────────────────────────────────────────────────────────────┐
  │  rootless dockerd (fuse-overlayfs)                                   │
  │                                                                      │
  │   ┌───────────────┐   spawns    ┌──────────────────────────────┐    │
  │   │ orchestrator   │ ─────────▶  │ agent-000  (GPU0)            │    │
  │   │  container      │            │   vLLM :8100  +  agent loop  │    │
  │   │ (docker socket) │            ├──────────────────────────────┤    │
  │   │  builds graph,  │            │ agent-001  (GPU1)            │    │
  │   │  seeds platform,│            │   vLLM :8101  +  agent loop  │    │
  │   │  launches N     │            ├──────────────────────────────┤    │
  │   │  agents         │            │ ...  agent-NNN (GPU N%8)     │    │
  │   └───────┬─────────┘            └──────────────┬───────────────┘    │
  │           │  HTTP (seed + stats)                │ HTTP actions       │
  │           ▼                                     ▼                    │
  │   ┌──────────────────────  platform container  :8000 ──────────────┐ │
  │   │  shared social world (users, posts, follows, traces) SQLite    │ │
  │   └────────────────────────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────────────────────┘
```

Only the **platform** (the social world) is shared. Each agent's LLM is private
to its container — that is the "LLM inside each docker" topology.

## Files

| File | Role |
| --- | --- |
| `Dockerfile.agent` | Agent image: `FROM vllm/vllm-openai` + OASIS agent code + personas. Runs `agent_entrypoint.sh`. |
| `agent_entrypoint.sh` | Boots the container's private vLLM, waits for health, then runs the OASIS agent loop against it + the shared platform. |
| `Dockerfile.orchestrator` | Controller image: Python + docker CLI + OASIS sim code. |
| `orchestrator_cluster.py` | Builds the social graph, seeds the platform, `docker run`s one agent per persona (round-robins GPUs, unique vLLM ports), waits, writes `cluster_summary.json`. |
| `run_cluster.sh` | One-command driver on the pod: build images → start platform → run orchestrator. |

The platform container reuses the existing `environment/oasis/platform/Dockerfile`.

## Why this needs the rootless-Docker recipe

The Greenland SDB pod is hostile to rootful Docker (its `/` is an overlay mount,
so dockerd's `overlay2` hits overlay-on-overlay and every container dies at
`runc: invalid rootfs`). The working recipe — installed by
`scripts/greenland-instance-setup.sh docker` — is **rootless Docker +
fuse-overlayfs (userspace overlay) + iproute2 (rootlesskit needs `ip`) +
`--pid=host` on every `docker run`**. The orchestrator passes `--pid=host`
automatically; `run_cluster.sh` does too for the platform.

Because the pod runs `hostNetwork: true`, all containers use `--network host`
and reach each other via `host.docker.internal` / fixed host ports. vLLM ports
are therefore made unique per agent (`--base-vllm-port + i`).

## Full run (from your laptop)

```bash
# 0. (laptop) auth + open the SSM tunnel to the NEW instance (port 1057)
./scripts/greenland-auth.sh
./scripts/greenland-connect.sh tunnel        # keep this terminal open

# 1. (laptop, new terminal) push code + set up conda AND rootless docker
./scripts/greenland-sync.sh deploy
./scripts/greenland-sync.sh run "bash scripts/greenland-instance-setup.sh docker"

# 2. (laptop) launch the cluster on the pod (8 agents, 20 steps, Qwen3-4B)
./scripts/greenland-sync.sh run "cd ~/MatrAIx && \
  export XDG_RUNTIME_DIR=\$HOME/.docker/run PATH=/usr/bin:\$PATH DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock && \
  environment/oasis/greenland/run_cluster.sh up 8 20 Qwen/Qwen3-4B"

# 3. (laptop) pull results back
./scripts/greenland-sync.sh pull environment/oasis/output/
```

Outputs land in `environment/oasis/output/`:
`cluster_summary.json` (run-level stats + per-agent exit codes),
`trajectory_NNN.json` (each agent's actions), `simulation.db` (full world state).

## Sizing / GPU math

Each agent runs a full vLLM. With `--gpu-mem-util 0.40` you fit ~2 agents per
A100, so **8 GPUs × 2 = 16 agents** is the comfortable ceiling for a 4–8B model.
Knobs (env vars or `run_cluster.sh` args):

| Knob | Default | Meaning |
| --- | --- | --- |
| `N_AGENTS` (arg 2) | 8 | number of agent containers / personas |
| `N_STEPS` (arg 3) | 20 | simulation steps per agent |
| `MODEL` (arg 4) | `Qwen/Qwen3-4B` | HF model id each agent serves |
| `NUM_GPUS` (env) | 8 | GPUs to round-robin across |
| `AGENTS_PER_GPU` (env) | 2 | informational ceiling check |
| `GPU_MEM_UTIL` (env) | 0.40 | vLLM mem fraction per agent |

If `N_AGENTS > NUM_GPUS × AGENTS_PER_GPU` the orchestrator warns and oversubscribes
(slower, may OOM). For a bigger fan-out at the same GPU budget, use the shared-vLLM
topology in the repo's `docker-compose.yaml` instead (one vLLM, many thin agents).

## Gotchas (carried from the verified recipe)

- **`DOCKER_HOST` is per-shell.** Every shell that runs `docker` (or `run_cluster.sh`)
  must export `XDG_RUNTIME_DIR`, `PATH=/usr/bin:$PATH`, and `DOCKER_HOST=unix://$HOME/.docker/run/docker.sock`.
- **`--pid=host` is mandatory** on this pod; the scripts already pass it.
- **First agent build is slow/large** (vLLM base image). Build once; reused across runs.
- **x86-only** images; the pod is x86 so that's fine.
- Re-running `setup docker` after a pod restart is required — rootless dockerd does
  not persist across pod recreation.

## Status

Built and unit-verified locally (graph seeding, user_id↔agent_id alignment, both
agent init paths; full OASIS suite = 149 passed). **Not yet executed on Greenland**
— that requires the interactive tunnel. Run the steps above and pull
`cluster_summary.json`; `agents_succeeded == num_agents` means a clean run.
