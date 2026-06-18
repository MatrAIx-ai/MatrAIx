import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from recbot.interecagent_bridge import (
    _build_chat_history,
    _last_recorded_plan,
    _latest_user_message,
    _planning_recording_file,
    _prepare_imports,
    main,
    run_turn,
)
from recbot.types import ChatMessage, RecBotRequest


class FakeAgent:
    def __init__(self):
        self._plan_record_cache = {
            "traj": [
                {"role": "user", "content": "Recommend a movie."},
                {"role": "plan", "content": "Action: ToolExecutor\nAction Input: not-json"},
            ]
        }
        self.candidate_buffer = type("FakeCandidateBuffer", (), {"track_info": {"lookups": []}})()

    def run(self, data, chat_history):
        return "fallback response"


class InteRecAgentBridgeTest(unittest.TestCase):
    def test_latest_user_message_uses_last_user_turn(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=3,
            messages=[
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood?"),
                ChatMessage(role="user", content="A tense thriller."),
            ],
        )

        self.assertEqual(_latest_user_message(request), "A tense thriller.")

    def test_build_chat_history_excludes_latest_user_message(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=3,
            messages=[
                ChatMessage(role="system", content="Use only the catalog."),
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood?"),
                ChatMessage(role="user", content="A tense thriller."),
            ],
        )

        history = _build_chat_history(request)

        self.assertIn("System: Use only the catalog.", history)
        self.assertIn("Human: Can you recommend a movie?", history)
        self.assertIn("Assistent: What mood?", history)
        self.assertNotIn("A tense thriller.", history)

    def test_prepare_imports_rejects_missing_root(self):
        missing_root = os.path.join(tempfile.gettempdir(), "missing_interecagent_root")

        with self.assertRaisesRegex(RuntimeError, "INTERECAGENT_ROOT does not exist"):
            _prepare_imports(missing_root, "movie")

    def test_prepare_imports_rejects_missing_resources_directory(self):
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "llm4crs"))

            with self.assertRaisesRegex(RuntimeError, "resources for domain 'movie' are missing"):
                _prepare_imports(root, "movie")

    def test_prepare_imports_moves_existing_root_to_front_of_sys_path(self):
        original_sys_path = list(sys.path)
        original_domain = os.environ.get("DOMAIN")

        try:
            with tempfile.TemporaryDirectory() as root:
                os.mkdir(os.path.join(root, "llm4crs"))
                os.makedirs(os.path.join(root, "resources", "movie"))
                resolved_root = os.path.realpath(root)
                sys.path.append(resolved_root)

                _prepare_imports(root, "movie")

                self.assertEqual(sys.path[0], resolved_root)
        finally:
            sys.path[:] = original_sys_path
            if original_domain is None:
                os.environ.pop("DOMAIN", None)
            else:
                os.environ["DOMAIN"] = original_domain

    def test_last_recorded_plan_returns_latest_plan_entry(self):
        agent = type(
            "FakeAgentWithPlans",
            (),
            {
                "_plan_record_cache": {
                    "traj": [
                        {"role": "plan", "content": "first plan"},
                        {"role": "assistant", "content": "intermediate"},
                        {"role": "plan", "content": "latest plan"},
                    ]
                }
            },
        )()

        self.assertEqual(_last_recorded_plan(agent), "latest plan")

    def test_run_turn_keeps_unparsed_plan_out_of_trace_plan_list(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=1,
            messages=[ChatMessage(role="user", content="Recommend a thriller.")],
        )

        with patch.dict(os.environ, {"INTERECAGENT_ROOT": "/fake/root"}, clear=True):
            with patch("recbot.interecagent_bridge._prepare_imports"), patch(
                "recbot.interecagent_bridge._build_interecagent",
                return_value=FakeAgent(),
            ):
                result = run_turn(request)

        self.assertEqual(result.assistant_message, "fallback response")
        self.assertEqual(result.native_action.raw_tool_plan, "not-json")
        self.assertEqual(result.trace.raw_tool_plan, [])

    def test_planning_recording_file_uses_env_or_default_temp_path(self):
        with patch.dict(os.environ, {"INTERECAGENT_PLANNING_RECORDING_FILE": "/tmp/custom.jsonl"}):
            self.assertEqual(_planning_recording_file(), "/tmp/custom.jsonl")

        with patch.dict(os.environ, {}, clear=True), patch(
            "recbot.interecagent_bridge.tempfile.gettempdir",
            return_value="/tmp/matraix-test",
        ):
            self.assertEqual(
                _planning_recording_file(),
                os.path.join("/tmp/matraix-test", "matraix_interecagent_plan.jsonl"),
            )

    def test_main_returns_one_when_interecagent_root_missing(self):
        payload = (
            '{"conversation_id":"episode_001","turn_id":1,'
            '"messages":[{"role":"user","content":"Recommend a thriller."}]}'
        )
        stderr = io.StringIO()

        with patch.dict(os.environ, {}, clear=True), patch("sys.stdin", io.StringIO(payload)):
            with redirect_stderr(stderr):
                exit_code = main()

        self.assertEqual(exit_code, 1)
        self.assertIn("INTERECAGENT_ROOT must be set", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
