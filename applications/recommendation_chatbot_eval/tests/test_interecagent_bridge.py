import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from recbot.interecagent_bridge import (
    _build_chat_history,
    _latest_user_message,
    _prepare_imports,
    main,
)
from recbot.types import ChatMessage, RecBotRequest


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
