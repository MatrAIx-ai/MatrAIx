from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, TextIO


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
CHAT_SCRIPT = APP_ROOT / "scripts" / "chat_interecagent_movie.py"
DEFAULT_MOVIE_CATALOG = (
    REPO_ROOT
    / "data"
    / "normalized"
    / "recommendation_catalogs"
    / "cmu_movie_summary"
    / "items.jsonl"
)
DEFAULT_MOVIE_RESOURCE_DIR = (
    REPO_ROOT
    / "data"
    / "cache"
    / "recommendation_chatbot_eval"
    / "recai_resources"
    / "movie"
)

APP_ROOT_TEXT = str(APP_ROOT)


def _is_app_root_path(path: str) -> bool:
    if not path:
        return False
    try:
        return Path(path).resolve() == APP_ROOT
    except OSError:
        return False


sys.path[:] = [path for path in sys.path if not _is_app_root_path(path)]
sys.path.insert(0, APP_ROOT_TEXT)

from recbot.types import ChatMessage, RecBotRequest, RecBotTurnResult


TEST_MESSAGES = [
    "I am in the mood for a mystery thriller.",
    "I like detective stories, but not supernatural horror.",
]


def _load_env_file(env: dict[str, str], path: Path) -> None:
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
        env.setdefault(key, value)


def _prepend_pythonpath(env: dict[str, str], path: Path) -> None:
    existing = env.get("PYTHONPATH", "")
    parts = [part for part in existing.split(os.pathsep) if part]
    path_text = str(path)
    if path_text not in parts:
        parts.insert(0, path_text)
    env["PYTHONPATH"] = os.pathsep.join(parts)


def _append_python_warning_filter(env: dict[str, str], rule: str) -> None:
    existing = env.get("PYTHONWARNINGS", "")
    rules = [item for item in existing.split(",") if item]
    if rule not in rules:
        rules.append(rule)
    env["PYTHONWARNINGS"] = ",".join(rules)


def _build_runtime_env(domain: str, *, env_file: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    _load_env_file(env, env_file or REPO_ROOT / ".env.local")
    env.setdefault("INTERECAGENT_DOMAIN", domain)
    env.setdefault("INTERECAGENT_RESOURCE_MODE", "matraix_catalog")
    env.setdefault("INTERECAGENT_RANKER_MODE", "semantic_profile")
    env.setdefault("INTERECAGENT_CACHE_AGENT", "1")
    if domain == "movie":
        env.setdefault("INTERECAGENT_CATALOG_PATH", str(DEFAULT_MOVIE_CATALOG))
    _prepend_pythonpath(env, APP_ROOT)
    _append_python_warning_filter(env, "ignore:resource_tracker:UserWarning")
    return env


def _python_executable(env: dict[str, str]) -> str:
    return env.get("INTERECAGENT_PYTHON") or sys.executable


def _chat_command(args: argparse.Namespace, env: dict[str, str] | None = None) -> list[str]:
    runtime_env = env or dict(os.environ)
    command = [
        _python_executable(runtime_env),
        str(CHAT_SCRIPT),
        "--conversation-id",
        args.conversation_id,
        "--domain",
        args.domain,
        "--backend-mode",
        args.backend_mode,
    ]
    if args.show_json:
        command.append("--show-json")
    return command


def _resource_dir(env: dict[str, str], domain: str) -> Path:
    configured = env.get("INTERECAGENT_GENERATED_RESOURCE_DIR")
    if configured:
        return Path(configured).expanduser()
    if domain == "movie":
        return DEFAULT_MOVIE_RESOURCE_DIR
    return (
        REPO_ROOT
        / "data"
        / "cache"
        / "recommendation_chatbot_eval"
        / "recai_resources"
        / domain
    )


def _preflight_errors(env: dict[str, str], domain: str) -> list[str]:
    errors: list[str] = []
    if not env.get("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is missing. Add it to .env.local or the shell environment.")

    interecagent_root = env.get("INTERECAGENT_ROOT")
    if not interecagent_root:
        errors.append("INTERECAGENT_ROOT is missing. Point it at the InteRecAgent checkout.")
    else:
        root = Path(interecagent_root).expanduser()
        if not root.exists():
            errors.append(f"INTERECAGENT_ROOT does not exist: {root}")
        elif not (root / "llm4crs").exists():
            errors.append(f"INTERECAGENT_ROOT must point to an InteRecAgent directory: {root}")

    interecagent_python = env.get("INTERECAGENT_PYTHON")
    if interecagent_python and not Path(interecagent_python).expanduser().exists():
        errors.append(f"INTERECAGENT_PYTHON does not exist: {interecagent_python}")

    catalog_path = Path(env.get("INTERECAGENT_CATALOG_PATH", "")).expanduser()
    if domain == "movie" and not catalog_path.exists():
        errors.append(
            "movie catalog is missing. Run: PYTHONPATH=applications/recommendation_chatbot_eval "
            "python applications/recommendation_chatbot_eval/scripts/normalize_cmu_movie_summary.py"
        )

    resources = _resource_dir(env, domain)
    item_info = resources / "item_info.parquet"
    item_sim = resources / "item_sim.npy"
    if not item_info.exists():
        errors.append(f"RecAI item_info.parquet is missing: {item_info}")
    if not item_sim.exists():
        errors.append(
            "RecAI item_sim.npy is missing. Run: python "
            "applications/recommendation_chatbot_eval/scripts/generate_item_similarity.py "
            "--resource-dir data/cache/recommendation_chatbot_eval/recai_resources/movie"
        )
    return errors


def _maybe_reexec_self(env: dict[str, str], argv: list[str]) -> None:
    configured = env.get("INTERECAGENT_PYTHON")
    if not configured or env.get("MATRAIX_RECBOT_CLI_REEXECED") == "1":
        return
    configured_path = Path(configured).expanduser().absolute()
    if Path(sys.executable).absolute() == configured_path:
        return
    env["MATRAIX_RECBOT_CLI_REEXECED"] = "1"
    os.execvpe(str(configured_path), [str(configured_path), str(Path(__file__).resolve()), *argv], env)


def _run_chat(
    args: argparse.Namespace,
    env: dict[str, str],
    *,
    exec_func: Callable[[str, list[str], dict[str, str]], Any] = os.execvpe,
) -> int:
    command = _chat_command(args, env)
    exec_func(command[0], command, env)
    return 0


def _tool_names(result: RecBotTurnResult) -> str:
    plan = result.native_action.raw_tool_plan if result.native_action else []
    if not isinstance(plan, list):
        plan = []
    names = [str(step.get("tool_name")) for step in plan if isinstance(step, dict) and step.get("tool_name")]
    return ", ".join(names) if names else "none"


def _executed_tool_names(result: RecBotTurnResult) -> str:
    outputs = result.trace.raw_tool_outputs
    if not isinstance(outputs, list):
        return "none"
    names = [str(entry.get("tool")) for entry in outputs if isinstance(entry, dict) and entry.get("tool")]
    return ", ".join(names[-4:]) if names else "none"


def _is_backend_retry_failure(result: RecBotTurnResult) -> bool:
    if result.assistant_message.strip().startswith("Something went wrong, please retry."):
        return True
    if not result.trace.recommended_item_ids:
        return True
    outputs = result.trace.raw_tool_outputs
    if not isinstance(outputs, list):
        return False
    for entry in outputs:
        if not isinstance(entry, dict):
            continue
        output = str(entry.get("output", "")).lower()
        if "something went wrong" in output or "there is no suitable items" in output:
            return True
    return False


def _print_test_summary(turns: list[RecBotTurnResult], stdout: TextIO, *, success: bool) -> None:
    print(
        "MatrAIx RecBot test completed" if success else "MatrAIx RecBot test failed",
        file=stdout,
    )
    print(f"conversation_id={turns[0].conversation_id if turns else 'none'}", file=stdout)
    print(f"turns={len(turns)}", file=stdout)
    for result in turns:
        assistant = " ".join(result.assistant_message.split())
        if len(assistant) > 180:
            assistant = assistant[:177] + "..."
        print(
            " ".join(
                [
                    f"turn {result.turn_id}:",
                    f"planned_tools={_tool_names(result)};",
                    f"executed_tools={_executed_tool_names(result)};",
                    f"recommended_ids={len(result.trace.recommended_item_ids)};",
                    f'assistant="{assistant}"',
                ]
            ),
            file=stdout,
        )


def _run_test_conversation(
    args: argparse.Namespace,
    *,
    run_turn_func: Callable[[RecBotRequest], RecBotTurnResult] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    if run_turn_func is None:
        import_stderr = io.StringIO()
        with redirect_stderr(import_stderr):
            from recbot.interecagent_bridge import run_turn as run_turn_func
        if args.verbose and import_stderr.getvalue():
            print(import_stderr.getvalue(), file=stderr, end="")

    messages = [
        ChatMessage(
            role="system",
            content=(
                "Use only the configured MatrAIx recommendation catalog. "
                "Ask a brief clarification question when the request is too broad."
            ),
        )
    ]
    turns: list[RecBotTurnResult] = []
    print("Running MatrAIx RecBot test...", file=stdout, flush=True)
    for turn_id, user_text in enumerate(TEST_MESSAGES, start=1):
        print(f"running turn {turn_id}/{len(TEST_MESSAGES)}", file=stdout, flush=True)
        messages.append(ChatMessage(role="user", content=user_text))
        request = RecBotRequest(
            conversation_id=args.conversation_id,
            turn_id=turn_id,
            messages=messages,
            metadata={"domain": args.domain},
        )
        backend_stdout = io.StringIO()
        backend_stderr = io.StringIO()
        with redirect_stdout(backend_stdout), redirect_stderr(backend_stderr):
            result = run_turn_func(request)
        if args.verbose and backend_stdout.getvalue():
            print(backend_stdout.getvalue(), file=stderr, end="")
        if args.verbose and backend_stderr.getvalue():
            print(backend_stderr.getvalue(), file=stderr, end="")
        turns.append(result)
        messages.append(ChatMessage(role="assistant", content=result.assistant_message))

    success = not any(_is_backend_retry_failure(turn) for turn in turns)
    _print_test_summary(turns, stdout, success=success)
    if args.show_json:
        print(json.dumps({"conversation_id": args.conversation_id, "turns": [turn.to_dict() for turn in turns]}, indent=2), file=stdout)
    return 0 if success else 1


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple CLI for the MatrAIx movie RecBot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    test_parser = subparsers.add_parser("test", help="Run a fixed 2-turn movie RecBot smoke test.")
    test_parser.add_argument("--conversation-id", default="local_movie_test")
    test_parser.add_argument("--domain", default="movie")
    test_parser.add_argument("--show-json", action="store_true")
    test_parser.add_argument("--verbose", action="store_true")
    test_parser.add_argument("--skip-preflight", action="store_true", help=argparse.SUPPRESS)

    chat_parser = subparsers.add_parser("chat", help="Start an interactive command-line movie RecBot chat.")
    chat_parser.add_argument("--conversation-id", default="local_movie_chat")
    chat_parser.add_argument("--domain", default="movie")
    chat_parser.add_argument("--show-json", action="store_true")
    chat_parser.add_argument(
        "--backend-mode",
        choices=["inprocess", "external"],
        default=os.environ.get("INTERECAGENT_CHAT_BACKEND_MODE", "inprocess"),
    )
    chat_parser.add_argument("--skip-preflight", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, force_exit_after_test: bool = False) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    args = _parse_args(argv)
    env = _build_runtime_env(args.domain)
    if not args.skip_preflight:
        errors = _preflight_errors(env, args.domain)
        if errors:
            for error in errors:
                print(f"RecBot setup error: {error}", file=sys.stderr)
            return 2

    if args.command == "chat":
        return _run_chat(args, env)

    _maybe_reexec_self(env, argv)
    os.environ.update(env)
    exit_code = _run_test_conversation(args)
    if force_exit_after_test:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(force_exit_after_test=True))
