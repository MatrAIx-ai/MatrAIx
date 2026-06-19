from __future__ import annotations

import json
import os
import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from recbot.provider import ExternalCommandConfig, ExternalCommandRecBotProvider, ProviderError
from recbot.types import ChatMessage, RecBotRequest


def _set_default_catalog_env() -> None:
    os.environ.setdefault("INTERECAGENT_RESOURCE_MODE", "matraix_catalog")
    os.environ.setdefault("INTERECAGENT_RANKER_MODE", "semantic_profile")
    os.environ.setdefault(
        "INTERECAGENT_CATALOG_PATH",
        str(APP_ROOT / "samples" / "cmu_movie_summary_tiny.jsonl"),
    )


def main() -> int:
    try:
        _set_default_catalog_env()
        bridge = APP_ROOT / "recbot" / "interecagent_bridge.py"
        python_executable = os.environ.get("INTERECAGENT_PYTHON", sys.executable)
        provider = ExternalCommandRecBotProvider(
            ExternalCommandConfig(
                command=[python_executable, str(bridge)],
                timeout_seconds=int(os.environ.get("INTERECAGENT_TIMEOUT_SECONDS", "180")),
            )
        )

        messages = [
            ChatMessage(
                role="system",
                content="Use the configured InteRecAgent catalog for recommendations.",
            ),
            ChatMessage(role="user", content="Can you recommend a movie for tonight?"),
        ]

        first = provider.next_turn(
            RecBotRequest(
                conversation_id="local_movie_smoke",
                turn_id=1,
                messages=messages,
                metadata={"domain": "movie"},
            )
        )

        messages.append(ChatMessage(role="assistant", content=first.assistant_message))
        messages.append(
            ChatMessage(
                role="user",
                content="I want something tense and mysterious, but not horror.",
            )
        )

        second = provider.next_turn(
            RecBotRequest(
                conversation_id="local_movie_smoke",
                turn_id=2,
                messages=messages,
                metadata={"domain": "movie"},
            )
        )

        json.dump(
            {
                "conversation_id": "local_movie_smoke",
                "turns": [first.to_dict(), second.to_dict()],
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    except (ProviderError, ValueError) as exc:
        print(f"smoke_interecagent_movie failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
