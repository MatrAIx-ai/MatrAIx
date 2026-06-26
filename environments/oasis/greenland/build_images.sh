#!/usr/bin/env bash
# build_images.sh — build the OASIS cluster images on the Greenland SDB pod.
#
# WHY THIS EXISTS (not a normal `docker build`):
# On this pod, `docker build` RUN steps fail with
#   error mounting "proc" to rootfs: operation not permitted
# because buildkit's build container can't get --pid=host (the pod forbids the
# /proc mount, and buildx exposes no per-RUN --pid=host). But `docker run
# --pid=host` works fine. So we build by: run a --pid=host container, exec the
# install steps inside it, COPY code in, then `docker commit` to an image.
#
# Produces: oasis-platform:latest, oasis-agent:latest
# (the orchestrator runs on the HOST via conda, so it needs no image.)
#
# Usage (on the pod, rootless docker env exported):
#   environments/oasis/greenland/build_images.sh [platform|agent|all]
set -uo pipefail
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$HOME/.docker/run}"
export PATH="/usr/bin:$PATH"
export DOCKER_HOST="${DOCKER_HOST:-unix://$HOME/.docker/run/docker.sock}"

REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_DIR"
WHAT="${1:-all}"

build_platform() {
    echo ">> Building oasis-platform via run+commit (base python:3.12-slim)..."
    docker rm -f bld-platform >/dev/null 2>&1 || true
    docker pull python:3.12-slim >/dev/null 2>&1 || true
    # Start a long-lived --pid=host container; copy code in; install deps inside it.
    docker run -d --name bld-platform --pid=host python:3.12-slim sleep 600 >/dev/null
    docker exec bld-platform mkdir -p /app
    docker cp environments bld-platform:/app/environments
    docker exec bld-platform pip install --no-cache-dir pyyaml requests fastapi uvicorn pydantic
    # Commit with the platform's runtime config baked in.
    docker commit \
        -c 'ENV DB_PATH=:memory:' -c 'ENV RECSYS_TYPE=random' \
        -c 'ENV MAX_REC_POSTS=50' -c 'ENV PORT=8000' \
        -c 'WORKDIR /app' -c 'EXPOSE 8000' \
        -c 'CMD python -c "import os,uvicorn;from environments.oasis.platform.server import create_app;uvicorn.run(create_app(db_path=os.environ[\"DB_PATH\"],recsys_type=os.environ[\"RECSYS_TYPE\"],max_rec_posts=int(os.environ[\"MAX_REC_POSTS\"])),host=\"0.0.0.0\",port=int(os.environ[\"PORT\"]))"' \
        bld-platform oasis-platform:latest
    docker rm -f bld-platform >/dev/null 2>&1 || true
    echo ">> ✓ oasis-platform:latest built"
}

build_agent() {
    echo ">> Building oasis-agent via run+commit (base vllm/vllm-openai)..."
    docker rm -f bld-agent >/dev/null 2>&1 || true
    docker pull vllm/vllm-openai:latest >/dev/null 2>&1 || true
    docker run -d --name bld-agent --pid=host --entrypoint sleep vllm/vllm-openai:latest 1200 >/dev/null
    docker exec bld-agent mkdir -p /app
    docker cp environments bld-agent:/app/environments
    docker cp personas bld-agent:/app/personas
    docker exec bld-agent cp /app/environments/oasis/greenland/agent_entrypoint.sh /app/agent_entrypoint.sh
    docker exec bld-agent chmod +x /app/agent_entrypoint.sh
    # curl for the in-container vLLM health probe; requests/pyyaml for the loop.
    docker exec bld-agent bash -lc 'pip install --no-cache-dir requests pyyaml >/dev/null 2>&1; (command -v curl >/dev/null 2>&1 || (apt-get update >/dev/null 2>&1 && apt-get install -y --no-install-recommends curl >/dev/null 2>&1)) || true'
    docker commit \
        -c 'WORKDIR /app' -c 'ENV PYTHONPATH=/app' \
        -c 'ENV PLATFORM_URL=http://host.docker.internal:8000' \
        -c 'ENV LLM_MODEL=Qwen/Qwen3-4B' -c 'ENV VLLM_PORT=8100' \
        -c 'ENV GPU_MEM_UTIL=0.40' -c 'ENV VLLM_MAX_LEN=4096' \
        -c 'ENV NUM_STEPS=20' -c 'ENV AGENT_ID=0' \
        -c 'ENTRYPOINT ["/app/agent_entrypoint.sh"]' \
        bld-agent oasis-agent:latest
    docker rm -f bld-agent >/dev/null 2>&1 || true
    echo ">> ✓ oasis-agent:latest built"
}

case "$WHAT" in
    platform) build_platform ;;
    agent)    build_agent ;;
    all)      build_platform; build_agent ;;
    *) echo "Usage: $0 [platform|agent|all]"; exit 1 ;;
esac
echo ">> images:"; docker images | grep -E 'oasis-(platform|agent)' || true
