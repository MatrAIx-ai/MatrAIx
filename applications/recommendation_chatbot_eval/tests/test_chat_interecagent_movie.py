import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.chat_interecagent_movie import _load_local_env


class ChatInterecagentMovieScriptTest(unittest.TestCase):
    def test_load_local_env_sets_missing_values_without_overriding_shell_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env.local"
            env_file.write_text(
                "\n".join(
                    [
                        "# local testing secrets",
                        "OPENAI_API_KEY=file-key",
                        "INTERECAGENT_ROOT=/tmp/RecAI-live/InteRecAgent",
                        "QUOTED_VALUE='quoted value'",
                        "DOUBLE_QUOTED=\"double quoted\"",
                        "MALFORMED_LINE",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
                _load_local_env(env_file)

                self.assertEqual(os.environ["OPENAI_API_KEY"], "shell-key")
                self.assertEqual(
                    os.environ["INTERECAGENT_ROOT"],
                    "/tmp/RecAI-live/InteRecAgent",
                )
                self.assertEqual(os.environ["QUOTED_VALUE"], "quoted value")
                self.assertEqual(os.environ["DOUBLE_QUOTED"], "double quoted")
                self.assertNotIn("MALFORMED_LINE", os.environ)


if __name__ == "__main__":
    unittest.main()
