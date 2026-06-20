import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import recbot
from recbot.types import NativeAction, RecBotTrace, RecBotTurnResult


class RecBotCliTest(unittest.TestCase):
    def test_build_runtime_env_loads_local_env_and_sets_catalog_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.local"
            env_file.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=file-key",
                        "INTERECAGENT_ROOT=/tmp/RecAI-live/InteRecAgent",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
                env = recbot._build_runtime_env("movie", env_file=env_file)

            self.assertEqual(env["OPENAI_API_KEY"], "shell-key")
            self.assertEqual(env["INTERECAGENT_ROOT"], "/tmp/RecAI-live/InteRecAgent")
            self.assertEqual(env["INTERECAGENT_RESOURCE_MODE"], "matraix_catalog")
            self.assertEqual(env["INTERECAGENT_RANKER_MODE"], "semantic_profile")
            self.assertIn(str(recbot.APP_ROOT), env["PYTHONPATH"].split(os.pathsep))

    def test_chat_command_execs_existing_interactive_chat_script(self):
        with patch.dict(os.environ, {"INTERECAGENT_PYTHON": "/tmp/recai-python"}, clear=True):
            command = recbot._chat_command(
                recbot._parse_args(["chat", "--show-json", "--conversation-id", "manual"])
            )

        self.assertEqual(command[0], "/tmp/recai-python")
        self.assertEqual(Path(command[1]).name, "chat_interecagent_movie.py")
        self.assertIn("--show-json", command)
        self.assertIn("manual", command)

    def test_run_test_conversation_prints_compact_two_turn_summary(self):
        calls = []

        def fake_run_turn(request):
            calls.append(request)
            return RecBotTurnResult(
                backend="fake",
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                user_message=request.latest_user_message,
                assistant_message=f"assistant turn {request.turn_id}",
                native_action=NativeAction(
                    raw="Action: ToolExecutor",
                    raw_tool_plan=[{"tool_name": "Movie Properties Filtering Tool"}],
                ),
                trace=RecBotTrace(
                    raw_tool_plan=[{"tool_name": "Movie Properties Filtering Tool"}],
                    raw_tool_outputs=[
                        {"tool": "Movie Properties Filtering Tool"},
                        {"tool": "Mapping Tool"},
                    ],
                    recommended_item_ids=[f"cmu:{request.turn_id}"],
                ),
            )

        output = io.StringIO()
        exit_code = recbot._run_test_conversation(
            recbot._parse_args(["test"]),
            run_turn_func=fake_run_turn,
            stdout=output,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].conversation_id, "local_movie_test")
        summary = output.getvalue()
        self.assertIn("MatrAIx RecBot test completed", summary)
        self.assertIn("turn 1", summary)
        self.assertIn("Movie Properties Filtering Tool", summary)
        self.assertIn("recommended_ids=1", summary)

    def test_run_test_conversation_fails_when_a_turn_has_no_recommended_ids(self):
        def fake_run_turn(request):
            return RecBotTurnResult(
                backend="fake",
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                user_message=request.latest_user_message,
                assistant_message="I need to refine the list.",
                native_action=NativeAction(raw="Final Answer: I need to refine the list."),
                trace=RecBotTrace(recommended_item_ids=[]),
            )

        output = io.StringIO()
        exit_code = recbot._run_test_conversation(
            recbot._parse_args(["test"]),
            run_turn_func=fake_run_turn,
            stdout=output,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("MatrAIx RecBot test failed", output.getvalue())

    def test_run_test_conversation_fails_on_backend_retry_response(self):
        def fake_run_turn(request):
            return RecBotTurnResult(
                backend="fake",
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                user_message=request.latest_user_message,
                assistant_message="Something went wrong, please retry.",
                native_action=NativeAction(raw="Final Answer: Something went wrong, please retry."),
                trace=RecBotTrace(),
            )

        output = io.StringIO()
        exit_code = recbot._run_test_conversation(
            recbot._parse_args(["test"]),
            run_turn_func=fake_run_turn,
            stdout=output,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("MatrAIx RecBot test failed", output.getvalue())

    def test_run_test_conversation_fails_on_broken_tool_output(self):
        def fake_run_turn(request):
            return RecBotTurnResult(
                backend="fake",
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                user_message=request.latest_user_message,
                assistant_message="Here are recommendations.",
                native_action=NativeAction(raw="Action: ToolExecutor"),
                trace=RecBotTrace(
                    raw_tool_outputs=[
                        {
                            "tool": "Movie Properties Filtering Tool",
                            "output": "Movie Properties Filtering Tool: something went wrong in execution",
                        }
                    ],
                    recommended_item_ids=["cmu:1"],
                ),
            )

        output = io.StringIO()
        exit_code = recbot._run_test_conversation(
            recbot._parse_args(["test"]),
            run_turn_func=fake_run_turn,
            stdout=output,
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("MatrAIx RecBot test failed", output.getvalue())

    def test_direct_script_help_uses_package_not_script_shadow(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(recbot.APP_ROOT)

        completed = subprocess.run(
            [sys.executable, str(recbot.APP_ROOT / "scripts" / "recbot.py"), "--help"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("{test,chat}", completed.stdout)


if __name__ == "__main__":
    unittest.main()
