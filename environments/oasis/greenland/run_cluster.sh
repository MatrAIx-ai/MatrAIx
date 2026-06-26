#!/usr/bin/env bash
# run_cluster.sh — bring up the full OASIS multi-agent Docker cluster ON the pod.
#
# Prereq: rootless Docker is already running (greenland-instance-setup.sh docker).
# This script must run on the Greenland instance, from the repo root (~/MatrAIx).
#
# Topology it creates:
#   - shared PLATFORM container (the social world) on host port 8000
#   - ORCHESTRATOR container (mounts the docker socket) that spawns N AGENT
#     containers, each carrying its own vLLM "brain", pinned to a GPU
#
# Usage:
#   environments/oasis/greenland/run_cluster.sh up   [N_AGENTS] [N_STEPS] [MODEL]
#   environments/oasis/greenland/run_cluster.sh build
#   environments/oasis/greenland/run_cluster.sh platform
#   environments/oasis/greenland/run_cluster.sh down
#   environments/oasis/greenland/run_cluster.sh logs
set -uo pipefail

# ---- rootless Docker env (must be present in THIS shell) --------------------
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$HOME/.docker/run}"
export PATH="/usr/bin:$PATH"
export DOCKER_HOST="${DOCKER_HOST:-unix://$HOME/.docker/run/docker.sock}"

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"   # ~/MatrAIx
cd "$REPO_DIR"

PLATFORM_IMAGE="oasis-platform:latest"
AGENT_IMAGE="oasis-agent:latest"
ORCH_IMAGE="oasis-orchestrator:latest"

N_AGENTS="${2:-8}"
N_STEPS="${3:-20}"
MODEL="${4:-Qwen/Qwen3-4B}"
NUM_GPUS="${NUM_GPUS:-8}"
AGENTS_PER_GPU="${AGENTS_PER_GPU:-2}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.40}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_DIR/environments/oasis/output}"
PLATFORM_URL="http://host.docker.internal:8000"

require_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "✗ rootless Docker not reachable. Run: scripts/greenland-instance-setup.sh docker"
        echo "  and make sure DOCKER_HOST=$DOCKER_HOST is exported in this shell."
        exit 1
    fi
}

build() {
    require_docker
    # NOTE: `docker build` RUN steps fail on this pod (/proc mount restriction).
    # We build via run+commit instead. The orchestrator runs on the HOST (conda),
    # so it needs no image.
    echo ">> Building images via run+commit (pod-safe)..."
    bash environments/oasis/greenland/build_images.sh all
    echo ">> ✓ images built"
}

platform() {
    require_docker
    mkdir -p "$OUTPUT_DIR"
    docker rm -f oasis-platform >/dev/null 2>&1 || true
    # Start from a CLEAN db: user_id is AUTOINCREMENT, so agent_id=i -> user_id=i+1
    # (which the graph edges assume) only holds on a fresh table. Reusing a db
    # would keep incrementing ids and misalign the social graph.
    rm -f "$OUTPUT_DIR/simulation.db" 2>/dev/null || true
    echo ">> Starting shared platform on host :8000 (fresh db) ..."
    docker run -d --name oasis-platform --init --pid=host --network host \
        -e DB_PATH=/app/output/simulation.db \
        -e RECSYS_TYPE=random -e MAX_REC_POSTS=50 -e PORT=8000 \
        -v "$OUTPUT_DIR:/app/output" \
        "$PLATFORM_IMAGE"
    echo ">> waiting for platform health..."
    for i in $(seq 1 30); do
        curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && { echo ">> ✓ platform healthy"; return 0; }
        sleep 2
    done
    echo "✗ platform did not become healthy; logs:"; docker logs --tail 30 oasis-platform; exit 1
}

orchestrate() {
    require_docker
    mkdir -p "$OUTPUT_DIR"
    echo ">> Launching orchestrator ON THE HOST: ${N_AGENTS} agents x ${N_STEPS} steps, model=${MODEL}"
    # IMPORTANT: the orchestrator runs on the HOST (not in a container), because
    # it `docker run`s sibling agent containers with -v host-path mounts. The
    # daemon resolves those -v paths on the host, so the orchestrator must pass
    # HOST paths (personas dir, output dir). Running it on the host via the
    # matraix conda env sidesteps all path-translation problems. It only needs
    # the docker CLI + the rootless DOCKER_HOST already exported above.
    #
    # Agent containers reach the platform via host.docker.internal:8000; on the
    # pod (hostNetwork) that resolves to the host where the platform container's
    # port 8000 is published.
    source "$HOME/miniconda3/etc/profile.d/conda.sh" 2>/dev/null && conda activate matraix 2>/dev/null || true
    python environments/oasis/greenland/orchestrator_cluster.py \
        --personas-dir "$REPO_DIR/personas/Jun20_1k_persona_description" \
        --num-agents "$N_AGENTS" --num-steps "$N_STEPS" \
        --agent-image "$AGENT_IMAGE" \
        --platform-url "$PLATFORM_URL" \
        --llm-model "$MODEL" \
        --num-gpus "$NUM_GPUS" --agents-per-gpu "$AGENTS_PER_GPU" \
        --gpu-mem-util "$GPU_MEM_UTIL" \
        --output-dir "$OUTPUT_DIR"
    echo ">> ✓ orchestrator finished. Summary: $OUTPUT_DIR/cluster_summary.json"
}

down() {
    require_docker
    echo ">> Stopping cluster containers..."
    docker rm -f oasis-orchestrator oasis-platform >/dev/null 2>&1 || true
    docker ps -a --format '{{.Names}}' | grep '^oasis-agent-' | xargs -r docker rm -f
    echo ">> ✓ cleaned up"
}

logs() {
    require_docker
    echo "=== platform ==="; docker logs --tail 20 oasis-platform 2>/dev/null || echo "(no platform)"
    echo "=== agents ==="; docker ps -a --format '{{.Names}}\t{{.Status}}' | grep '^oasis-agent-' || echo "(no agents)"
}

case "${1:-help}" in
    build)     build ;;
    platform)  platform ;;
    orchestrate) orchestrate ;;
    up)        build; platform; orchestrate ;;
    down)      down ;;
    logs)      logs ;;
    *) echo "Usage: $0 [up|build|platform|orchestrate|down|logs] [N_AGENTS] [N_STEPS] [MODEL]" ;;
esac
