from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT))

from recbot.provider import ExternalCommandConfig, ExternalCommandRecBotProvider, ProviderError
from recbot.types import ChatMessage, RecBotRequest


def _load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _set_default_catalog_env(domain: str) -> None:
    os.environ.setdefault("INTERECAGENT_RESOURCE_MODE", "matraix_catalog")
    os.environ.setdefault("INTERECAGENT_RANKER_MODE", "semantic_profile")
    os.environ.setdefault("INTERECAGENT_CACHE_AGENT", "1")
    if domain == "movie":
        catalog_path = (
            REPO_ROOT
            / "data"
            / "normalized"
            / "recommendation_catalogs"
            / "cmu_movie_summary"
            / "items.jsonl"
        )
        if not catalog_path.exists():
            raise RuntimeError(
                "full CMU movie catalog is required. Run "
                "`PYTHONPATH=applications/recommendation_chatbot_eval "
                "python applications/recommendation_chatbot_eval/scripts/normalize_cmu_movie_summary.py` first."
            )
        os.environ.setdefault(
            "INTERECAGENT_CATALOG_PATH",
            str(catalog_path),
        )


def _build_provider() -> ExternalCommandRecBotProvider:
    bridge = APP_ROOT / "recbot" / "interecagent_bridge.py"
    python_executable = os.environ.get("INTERECAGENT_PYTHON", sys.executable)
    return ExternalCommandRecBotProvider(
        ExternalCommandConfig(
            command=[python_executable, str(bridge)],
            timeout_seconds=int(os.environ.get("INTERECAGENT_TIMEOUT_SECONDS", "180")),
        )
    )


def _maybe_reexec_with_configured_python() -> None:
    configured = os.environ.get("INTERECAGENT_PYTHON")
    if not configured or os.environ.get("MATRAIX_RECBOT_REEXECED") == "1":
        return
    configured_path = Path(configured).expanduser().absolute()
    if Path(sys.executable).absolute() == configured_path:
        return
    os.environ["MATRAIX_RECBOT_REEXECED"] = "1"
    os.execv(str(configured_path), [str(configured_path), *sys.argv])


def _next_turn_inprocess(request: RecBotRequest):
    from recbot.interecagent_bridge import run_turn

    backend_stdout = io.StringIO()
    with redirect_stdout(backend_stdout):
        result = run_turn(request)
    backend_output = backend_stdout.getvalue()
    if backend_output:
        print(backend_output, file=sys.stderr, end="")
    return result


def main() -> int:
    _load_local_env(REPO_ROOT / ".env.local")
    _maybe_reexec_with_configured_python()

    parser = argparse.ArgumentParser(description="Chat with the catalog-backed movie RecBot.")
    parser.add_argument("--conversation-id", default="local_movie_chat")
    parser.add_argument("--domain", default=os.environ.get("INTERECAGENT_DOMAIN", "movie"))
    parser.add_argument("--show-json", action="store_true")
    parser.add_argument(
        "--backend-mode",
        choices=["inprocess", "external"],
        default=os.environ.get("INTERECAGENT_CHAT_BACKEND_MODE", "inprocess"),
    )
    args = parser.parse_args()

    _set_default_catalog_env(args.domain)
    provider = _build_provider() if args.backend_mode == "external" else None
    messages = [
        ChatMessage(
            role="system",
            content=(
                "Use only the configured MatrAIx recommendation catalog. "
                "Ask a brief clarification question when the request is too broad."
            ),
        )
    ]

    print("MatrAIx RecBot. Type 'quit' or 'exit' to stop.")
    turn_id = 1
    while True:
        try:
            user_text = input("You> ").strip()
        except EOFError:
            print()
            return 0
        if not user_text:
            continue
        if user_text.lower() in {"quit", "exit"}:
            return 0

        messages.append(ChatMessage(role="user", content=user_text))
        try:
            request = RecBotRequest(
                conversation_id=args.conversation_id,
                turn_id=turn_id,
                messages=messages,
                metadata={"domain": args.domain},
            )
            result = (
                provider.next_turn(request)
                if provider is not None
                else _next_turn_inprocess(request)
            )
        except (ProviderError, RuntimeError, ValueError) as exc:
            print(f"RecBot error: {exc}", file=sys.stderr)
            return 1

        print(f"Agent> {result.assistant_message}")
        if args.show_json:
            print(json.dumps(result.to_dict(), indent=2))
        messages.append(ChatMessage(role="assistant", content=result.assistant_message))
        turn_id += 1


if __name__ == "__main__":
    raise SystemExit(main())
