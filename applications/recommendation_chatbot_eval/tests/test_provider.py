import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from recbot.provider import ExternalCommandConfig, ExternalCommandRecBotProvider, ProviderError
from recbot.types import ChatMessage, RecBotRequest


class ExternalCommandProviderTest(unittest.TestCase):
    def test_provider_sends_request_and_reads_turn_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "fake_bridge.py"
            script.write_text(
                textwrap.dedent(
                    """
                    import json
                    import sys

                    payload = json.load(sys.stdin)
                    latest_user = [m["content"] for m in payload["messages"] if m["role"] == "user"][-1]
                    json.dump(
                        {
                            "backend": "fake",
                            "conversation_id": payload["conversation_id"],
                            "turn_id": payload["turn_id"],
                            "user_message": latest_user,
                            "assistant_message": "fake response",
                            "native_action": {"raw": "Final Answer: fake response", "raw_tool_plan": None},
                            "trace": {
                                "raw_tool_plan": None,
                                "raw_tool_outputs": None,
                                "recommended_item_ids": [],
                            },
                        },
                        sys.stdout,
                    )
                    """
                ).strip()
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            result = provider.next_turn(request)

            self.assertEqual(result.backend, "fake")
            self.assertEqual(result.user_message, "Recommend a movie.")
            self.assertEqual(result.assistant_message, "fake response")

    def test_provider_raises_on_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "bad_bridge.py"
            script.write_text("import sys\nsys.stderr.write('boom')\nsys.exit(7)\n")
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            with self.assertRaises(ProviderError) as context:
                provider.next_turn(request)

            self.assertIn("exit code 7", str(context.exception))

    def test_provider_raises_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "invalid_json_bridge.py"
            script.write_text("print('not json')\n")
            provider = ExternalCommandRecBotProvider(
                ExternalCommandConfig(command=[sys.executable, str(script)], timeout_seconds=10)
            )
            request = RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="user", content="Recommend a movie.")],
            )

            with self.assertRaises(ProviderError) as context:
                provider.next_turn(request)

            self.assertIn("invalid JSON", str(context.exception))


if __name__ == "__main__":
    unittest.main()
