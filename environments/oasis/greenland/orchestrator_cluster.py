#!/usr/bin/env python3
"""orchestrator_cluster.py — the "orchestrator docker" that manages agent dockers.

This is the controller container in the multi-agent OASIS setup. It does NOT run
any LLM itself. It:

  1. loads N personas + builds the social graph (reuses environments.oasis.network),
  2. seeds the SHARED platform service (signup users, bulk-follow edges, seed posts)
     over HTTP,
  3. spins up ONE agent container per persona via the Docker socket
     (`docker run --pid=host --gpus ...`), each carrying its own vLLM "brain",
  4. spreads agents across the 8 A100s (configurable agents-per-GPU) and assigns
     each a private vLLM port,
  5. waits for all agent containers to finish their NUM_STEPS, streaming logs,
  6. pulls final stats/traces from the platform and writes a run summary.

It talks to Docker through the rootless socket (mounted into this container, or
used directly when run on the host). Every `docker run` includes --pid=host,
which is mandatory on the Greenland SDB pod (see greenland-instance-setup.sh).

Run inside the orchestrator container (see Dockerfile.orchestrator) OR directly
on the host with the rootless DOCKER_HOST exported. Example (host):

    export XDG_RUNTIME_DIR=$HOME/.docker/run PATH=/usr/bin:$PATH \
        DOCKER_HOST=unix://$HOME/.docker/run/docker.sock
    python environments/oasis/greenland/orchestrator_cluster.py \
        --personas-dir personas/Jun20_1k_persona_description \
        --num-agents 8 --num-steps 20 \
        --agent-image oasis-agent:latest \
        --llm-model Qwen/Qwen3-4B --agents-per-gpu 2 --num-gpus 8
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app")
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import requests  # noqa: E402

from environments.oasis.network import build_social_graph, NetworkConfig  # noqa: E402
from environments.oasis.persona_loader import load_personas_from_directory  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [orchestrator] %(message)s")
log = logging.getLogger("orchestrator")


def wait_for_platform(platform_url: str, timeout_s: int = 120) -> None:
    """Block until the shared platform's /health is up."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = requests.get(f"{platform_url}/health", timeout=3)
            if r.ok:
                log.info(f"platform healthy at {platform_url}")
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError(f"platform at {platform_url} never became healthy")


def seed_platform(platform_url: str, personas, graph) -> None:
    """Register users in index order, install follow edges, inject seed posts.

    Users are seeded with agent_id == list index, so the platform assigns
    user_id == index + 1 (the DB autoincrements in insert order). This matches
    the graph edges, which reference idx + 1. Each agent container is later told
    its CLUSTER_AGENT_ID == index and resolves its user_id via /state/{agent_id},
    so it never re-signs-up with a clashing id.
    """
    users = [
        {
            "agent_id": i,
            "user_name": p.user_name,
            "name": p.name,
            "bio": p.bio,
        }
        for i, p in enumerate(personas)
    ]
    r = requests.post(f"{platform_url}/signup/bulk", json={"users": users}, timeout=60)
    r.raise_for_status()
    log.info(f"seeded {r.json().get('registered', len(users))} users on platform (agent_id == index)")

    if graph is not None and graph.edges:
        edges = [[e.follower_idx + 1, e.followee_idx + 1] for e in graph.edges]
        requests.post(f"{platform_url}/follow/bulk", json={"edges": edges}, timeout=60)
        log.info(f"installed {len(edges)} follow edges")
        for sp in graph.seed_posts:
            requests.post(
                f"{platform_url}/seed_post",
                json={"user_id": sp.author_idx + 1, "content": sp.content},
                timeout=30,
            )
        log.info(f"injected {len(graph.seed_posts)} seed posts")


def docker_run_agent(
    *,
    agent_image: str,
    agent_id: int,
    persona_path: str,
    platform_url: str,
    llm_model: str,
    vllm_port: int,
    gpu_index: int,
    gpu_mem_util: float,
    num_steps: int,
    output_dir: str,
    network: str,
    extra_run_args: list[str],
) -> str:
    """Launch one agent container (detached). Returns the container name."""
    name = f"oasis-agent-{agent_id:03d}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)  # clear stale

    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "--pid=host",                                  # MANDATORY on the SDB pod
        "--device", f"nvidia.com/gpu={gpu_index}",    # CDI GPU (rootless-safe; NOT --gpus)
        "--network", network,                          # "host" on the pod (hostNetwork)
        "--add-host", "host.docker.internal:host-gateway",
        "-e", f"AGENT_ID={agent_id}",
        "-e", f"CLUSTER_AGENT_ID={agent_id}",          # pre-seeded mode: resolve user_id by agent_id
        "-e", f"PERSONA_PATH={persona_path}",
        "-e", f"PLATFORM_URL={platform_url}",
        "-e", f"LLM_MODEL={llm_model}",
        "-e", f"VLLM_PORT={vllm_port}",
        "-e", f"GPU_MEM_UTIL={gpu_mem_util}",
        "-e", f"NUM_STEPS={num_steps}",
        "-e", f"OUTPUT_PATH=/app/output/trajectory_{agent_id:03d}.json",
        "-v", f"{output_dir}:/app/output",
        *extra_run_args,
        agent_image,
    ]
    log.info(f"launching {name} on GPU {gpu_index}, vLLM port {vllm_port}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        log.error(f"failed to launch {name}: {res.stderr.strip()}")
        raise RuntimeError(res.stderr.strip())
    return name


def wait_for_containers(names: list[str], poll_s: int = 10) -> dict[str, int]:
    """Block until all agent containers exit; return name -> exit code."""
    remaining = set(names)
    exit_codes: dict[str, int] = {}
    while remaining:
        time.sleep(poll_s)
        for name in list(remaining):
            res = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}} {{.State.ExitCode}}", name],
                capture_output=True, text=True,
            )
            out = res.stdout.strip()
            if not out:
                continue
            running, code = (out.split() + ["?"])[:2]
            if running == "false":
                exit_codes[name] = int(code) if code.isdigit() else -1
                remaining.discard(name)
                log.info(f"{name} finished (exit {exit_codes[name]}); {len(remaining)} remaining")
    return exit_codes


def main() -> int:
    ap = argparse.ArgumentParser(description="OASIS multi-agent Docker orchestrator")
    ap.add_argument("--personas-dir", default="personas/Jun20_1k_persona_description",
                    help="dir the orchestrator reads personas from (HOST path) to build the graph")
    ap.add_argument("--container-personas-dir", default="personas/Jun20_1k_persona_description",
                    help="dir the agent IMAGE has personas at (repo-relative; COPYd to /app)")
    ap.add_argument("--num-agents", type=int, default=8)
    ap.add_argument("--num-steps", type=int, default=20)
    ap.add_argument("--agent-image", default="oasis-agent:latest")
    ap.add_argument("--platform-url", default="http://host.docker.internal:8000")
    ap.add_argument("--llm-model", default="Qwen/Qwen3-4B")
    ap.add_argument("--num-gpus", type=int, default=8)
    ap.add_argument("--agents-per-gpu", type=int, default=2)
    ap.add_argument("--gpu-mem-util", type=float, default=0.40)
    ap.add_argument("--base-vllm-port", type=int, default=8100)
    ap.add_argument("--network", default="host", help="docker network (host on the SDB pod)")
    ap.add_argument("--output-dir", default="/app/output")
    ap.add_argument("--random-seed", type=int, default=42)
    ap.add_argument("--extra-run-arg", action="append", default=[],
                    help="extra arg passed verbatim to each `docker run` (repeatable)")
    args = ap.parse_args()

    capacity = args.num_gpus * args.agents_per_gpu
    if args.num_agents > capacity:
        log.warning(
            f"num_agents={args.num_agents} exceeds GPU capacity "
            f"({args.num_gpus} GPUs x {args.agents_per_gpu}/GPU = {capacity}); "
            f"agents will oversubscribe GPUs (slower / may OOM)."
        )

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    log.info(f"loading up to {args.num_agents} personas from {args.personas_dir}")
    personas = load_personas_from_directory(args.personas_dir, max_agents=args.num_agents)
    # Mirror the loader's ordering EXACTLY (sorted glob) so index i maps to the
    # same file the persona at index i was built from. This is the path mounted
    # into agent container i, and it lines up with CLUSTER_AGENT_ID == i.
    persona_files = sorted(Path(args.personas_dir).glob("*.yaml")) or \
        sorted(Path(args.personas_dir).glob("*.yml"))
    persona_files = persona_files[:len(personas)]
    log.info(f"loaded {len(personas)} personas ({len(persona_files)} files)")

    graph = build_social_graph(personas, NetworkConfig(random_seed=args.random_seed))

    wait_for_platform(args.platform_url)
    seed_platform(args.platform_url, personas, graph)

    # Launch one container per persona, round-robining GPUs and unique ports.
    names: list[str] = []
    for i, p in enumerate(personas):
        gpu_index = i % args.num_gpus
        vllm_port = args.base_vllm_port + i  # unique per agent (host network -> ports must not clash)
        # Path INSIDE the agent image: personas/ is COPYd into /app, so the
        # container sees the file at <container_personas_dir>/<filename>. We do
        # NOT pass the host path here (the agent container doesn't have it).
        persona_file = f"{args.container_personas_dir}/{persona_files[i].name}"
        names.append(docker_run_agent(
            agent_image=args.agent_image,
            agent_id=i,
            persona_path=persona_file,
            platform_url=args.platform_url,
            llm_model=args.llm_model,
            vllm_port=vllm_port,
            gpu_index=gpu_index,
            gpu_mem_util=args.gpu_mem_util,
            num_steps=args.num_steps,
            output_dir=args.output_dir,
            network=args.network,
            extra_run_args=args.extra_run_arg,
        ))

    log.info(f"launched {len(names)} agent containers; waiting for completion...")
    exit_codes = wait_for_containers(names)

    # Collect final world state from the platform.
    stats, traces = {}, []
    try:
        stats = requests.get(f"{args.platform_url}/stats", timeout=30).json()
        traces = requests.get(f"{args.platform_url}/traces", timeout=60).json()
    except requests.RequestException as e:
        log.warning(f"could not pull final platform state: {e}")

    summary = {
        "num_agents": len(names),
        "num_steps": args.num_steps,
        "llm_model": args.llm_model,
        "num_gpus": args.num_gpus,
        "agents_per_gpu": args.agents_per_gpu,
        "agent_exit_codes": exit_codes,
        "agents_succeeded": sum(1 for c in exit_codes.values() if c == 0),
        "platform_stats": stats,
        "trace_count": len(traces) if isinstance(traces, list) else None,
    }
    out_path = Path(args.output_dir) / "cluster_summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    log.info(f"run complete. summary -> {out_path}")
    log.info(json.dumps(summary, indent=2))
    return 0 if summary["agents_succeeded"] == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())
