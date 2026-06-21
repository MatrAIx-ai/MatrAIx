# entrypoint.py — Docker container entry point for a single agent.
# Reads config from environment variables, initializes, and runs the agent loop.

from __future__ import annotations

import json
import logging
import os
import sys

sys.path.insert(0, "/app")

from environments.oasis.agents.runner import AgentConfig, AgentRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("agent")


def main():
    config = AgentConfig(
        persona_path=os.environ.get("PERSONA_PATH", ""),
        platform_url=os.environ.get("PLATFORM_URL", "http://localhost:8000"),
        llm_base_url=os.environ.get("LLM_BASE_URL", "http://localhost:8002/v1"),
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        llm_model=os.environ.get("LLM_MODEL", "Qwen/Qwen3-4B"),
        llm_temperature=float(os.environ.get("LLM_TEMPERATURE", "0.7")),
        llm_max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "512")),
        available_actions=os.environ.get("AVAILABLE_ACTIONS", "create_post,like_post,repost,follow,do_nothing").split(","),
    )

    num_steps = int(os.environ.get("NUM_STEPS", "5"))

    logger.info(f"Starting agent | persona={config.persona_path} | model={config.llm_model} | steps={num_steps}")

    agent = AgentRunner(config)
    user_id = agent.initialize()
    logger.info(f"Registered as user_id={user_id} ({agent.persona.name})")

    results = agent.run(num_steps=num_steps)

    for r in results:
        actions_str = ", ".join(a["action"] for a in r.actions_taken)
        logger.info(f"Step {r.step}: [{actions_str}] ({r.duration_ms}ms)")

    output_path = os.environ.get("OUTPUT_PATH", "/app/output/trajectory.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump([{
            "step": r.step,
            "user_id": r.user_id,
            "actions": r.actions_taken,
            "duration_ms": r.duration_ms,
            "error": r.error,
        } for r in results], f, indent=2)

    logger.info(f"Done. {len(results)} steps completed. Trajectory saved to {output_path}")


if __name__ == "__main__":
    main()
