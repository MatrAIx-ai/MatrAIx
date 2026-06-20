import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import pandas as pd

from recbot.interecagent_bridge import (
    _CatalogSimilarityTool,
    _SeedExcludingSimilarityAdapter,
    _build_chat_history,
    _force_hard_filter_selectable_sql,
    _last_recorded_plan,
    _latest_user_message,
    _planning_recording_file,
    _prepare_imports,
    _similarity_mode,
    main,
    run_turn,
)
from recbot.types import ChatMessage, RecBotRequest
from recbot.types import RecBotTurnResult


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


class FakeEmptyPlanAgent:
    def __init__(self):
        self._plan_record_cache = {
            "traj": [
                {
                    "role": "plan",
                    "content": "Action: ToolExecutor\nAction Input: []",
                }
            ]
        }
        self.candidate_buffer = type("FakeCandidateBuffer", (), {"track_info": ""})()

    def run(self, data, chat_history):
        return "Something went wrong, please retry."


class FakeTrackerAgent:
    def __init__(self):
        self._plan_record_cache = {
            "traj": [
                {
                    "role": "plan",
                    "content": (
                        "Action: ToolExecutor\n"
                        "Action Input: [{\"tool_name\": \"Movie Properties Filtering Tool\", "
                        "\"input\": \"SELECT * FROM movie_information\"}]"
                    ),
                }
            ]
        }
        self.candidate_buffer = FakeTrackerBuffer()

    def run(self, data, chat_history):
        return "Here are two movies."


class FakeTrackerBuffer:
    def __init__(self):
        self.tracker = [
            {
                "tool": "Movie Properties Filtering Tool",
                "input": "SELECT * FROM movie_information",
                "output": "After Movie Properties Filtering Tool: There are 2 eligible items.",
            }
        ]

    @property
    def track_info(self):
        return "0: Movie Properties Filtering Tool (input: ..., output: ...);"


class FakeSimilarityInnerTool:
    name = "Movie Similarity Filtering Tool"
    desc = "find similar movies"

    def __init__(self, buffer):
        self.buffer = buffer

    def run(self, inputs):
        self.buffer.memory = [1, 2, 3]
        self.buffer.track(self.name, inputs, "native output")
        return "native output"


class FakeSeedCorpus:
    def fuzzy_match(self, value, col):
        if isinstance(value, list):
            return value
        return value

    def convert_title_2_info(self, titles, col_names=None):
        title_to_id = {"Aurora Station": 1}
        if isinstance(titles, str):
            return {"id": title_to_id[titles]}
        return {"id": [title_to_id[title] for title in titles if title in title_to_id]}


class FakeSeedBuffer:
    def __init__(self):
        self.memory = []
        self.tracker = []
        self.similarity = None

    def get(self):
        return list(self.memory)

    def push(self, tool, candidates):
        self.memory = list(candidates)

    def track(self, tool, input=None, output=None):
        self.tracker.append({"tool": tool, "input": input, "output": output})

    def save_similarity(self, sim):
        self.similarity = sim


class FakeCatalogSimilarityCorpus:
    def __init__(self):
        self.corups = pd.DataFrame(
            [
                {
                    "id": 1,
                    "title": "Aurora Station",
                    "tags": "Science Fiction, Thriller, Mystery",
                    "description": "Orbital station signal mystery.",
                    "display_text": "Science fiction thriller mystery in orbit.",
                },
                {
                    "id": 2,
                    "title": "Nebula Code",
                    "tags": "Science Fiction, Mystery",
                    "description": "Engineers decode a distant signal.",
                    "display_text": "Science fiction mystery about a distant signal.",
                },
                {
                    "id": 3,
                    "title": "The Orchard House",
                    "tags": "Drama, Family",
                    "description": "A warm family drama.",
                    "display_text": "Family drama on a farm.",
                },
            ]
        ).set_index("id", drop=True)

    def __len__(self):
        return 4

    def fuzzy_match(self, value, col):
        return value

    def convert_title_2_info(self, titles, col_names=None):
        title_to_id = {"Aurora Station": 1, "Nebula Code": 2, "The Orchard House": 3}
        if isinstance(titles, str):
            return {"id": title_to_id[titles]}
        return {"id": [title_to_id[title] for title in titles]}


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

    def test_prepare_imports_allows_missing_resources_directory_by_default(self):
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "llm4crs"))

            _prepare_imports(root, "movie")

            self.assertEqual(sys.path[0], os.path.realpath(root))

    def test_prepare_imports_rejects_missing_resources_directory_when_required(self):
        with tempfile.TemporaryDirectory() as root:
            os.mkdir(os.path.join(root, "llm4crs"))

            with self.assertRaisesRegex(RuntimeError, "resources for domain 'movie' are missing"):
                _prepare_imports(root, "movie", require_resources=True)

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

    def test_force_hard_filter_selectable_sql_keeps_where_clause_and_selects_all(self):
        sql = "SELECT title FROM movie_information WHERE tags LIKE '%Thriller%' ORDER BY visited_num DESC"

        normalized = _force_hard_filter_selectable_sql(sql)

        self.assertEqual(
            normalized,
            "SELECT * FROM movie_information WHERE display_text LIKE '%Thriller%' ORDER BY visited_num DESC",
        )

    def test_force_hard_filter_selectable_sql_preserves_unknown_negative_tags(self):
        sql = "SELECT title FROM movie_information WHERE tags LIKE '%Mystery%' AND tags NOT LIKE '%Horror%'"

        normalized = _force_hard_filter_selectable_sql(sql)

        self.assertEqual(
            normalized,
            "SELECT * FROM movie_information WHERE display_text LIKE '%Mystery%' AND display_text NOT LIKE '%Horror%'",
        )

    def test_seed_excluding_similarity_adapter_removes_seed_item_from_candidates(self):
        buffer = FakeSeedBuffer()
        inner = FakeSimilarityInnerTool(buffer)
        adapter = _SeedExcludingSimilarityAdapter(inner, FakeSeedCorpus(), buffer)

        output = adapter.run('["Aurora Station"]')

        self.assertEqual(buffer.get(), [2, 3])
        self.assertIn("Removed seed items", output)
        self.assertIn("Removed seed items", buffer.tracker[-1]["output"])

    def test_similarity_mode_uses_catalog_text_for_large_matraix_catalog(self):
        with patch.dict(os.environ, {"INTERECAGENT_DENSE_SIMILARITY_MAX_ITEMS": "2"}):
            self.assertEqual(_similarity_mode("matraix_catalog", 3), "catalog_text")
            self.assertEqual(_similarity_mode("matraix_catalog", 2), "native")
            self.assertEqual(_similarity_mode("recai_resources", 10), "native")

    def test_catalog_similarity_tool_selects_similar_items_from_catalog_metadata(self):
        buffer = FakeSeedBuffer()
        buffer.memory = [1, 2, 3]
        tool = _CatalogSimilarityTool(
            name="Movie Similarity Filtering Tool",
            desc="find similar movies",
            item_corpus=FakeCatalogSimilarityCorpus(),
            buffer=buffer,
            top_ratio=0.75,
        )

        output = tool.run('["Aurora Station"]')

        self.assertEqual(buffer.get(), [2])
        self.assertIn("full catalog text and metadata", output)
        self.assertEqual(buffer.tracker[-1]["tool"], "Movie Similarity Filtering Tool")

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

    def test_run_turn_captures_recai_tracker_as_raw_tool_outputs(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=1,
            messages=[ChatMessage(role="user", content="Recommend a thriller.")],
        )

        with patch.dict(os.environ, {"INTERECAGENT_ROOT": "/fake/root"}, clear=True):
            with patch("recbot.interecagent_bridge._prepare_imports"), patch(
                "recbot.interecagent_bridge._build_interecagent",
                return_value=FakeTrackerAgent(),
            ):
                result = run_turn(request)

        self.assertEqual(
            result.trace.raw_tool_outputs,
            [
                {
                    "tool": "Movie Properties Filtering Tool",
                    "input": "SELECT * FROM movie_information",
                    "output": "After Movie Properties Filtering Tool: There are 2 eligible items.",
                }
            ],
        )

    def test_run_turn_exposes_current_user_request_for_catalog_ranker(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=1,
            messages=[ChatMessage(role="user", content="I like Batman. Recommend a movie.")],
        )

        with patch.dict(os.environ, {"INTERECAGENT_ROOT": "/fake/root"}, clear=True):
            with patch("recbot.interecagent_bridge._prepare_imports"), patch(
                "recbot.interecagent_bridge._build_interecagent",
                return_value=FakeAgent(),
            ):
                run_turn(request)

            self.assertEqual(
                os.environ.get("MATRAIX_CURRENT_USER_REQUEST"),
                "I like Batman. Recommend a movie.",
            )

    def test_run_turn_repairs_empty_tool_plan_failure_as_clarification(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=1,
            messages=[ChatMessage(role="user", content="I want to watch a movie.")],
        )

        with patch.dict(os.environ, {"INTERECAGENT_ROOT": "/fake/root"}, clear=True):
            with patch("recbot.interecagent_bridge._prepare_imports"), patch(
                "recbot.interecagent_bridge._build_interecagent",
                return_value=FakeEmptyPlanAgent(),
            ):
                result = run_turn(request)

        self.assertIn("What kind of movie", result.assistant_message)
        self.assertNotIn("Something went wrong", result.assistant_message)
        self.assertEqual(result.native_action.raw_tool_plan, [])

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

    def test_main_keeps_backend_stdout_noise_out_of_result_json(self):
        payload = (
            '{"conversation_id":"episode_001","turn_id":1,'
            '"messages":[{"role":"user","content":"Recommend a thriller."}]}'
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        def noisy_run_turn(request):
            print("Columns in item corups: noisy backend output")
            return RecBotTurnResult(
                backend="interecagent",
                conversation_id=request.conversation_id,
                turn_id=request.turn_id,
                user_message=request.latest_user_message,
                assistant_message="A recommendation.",
            )

        with patch("recbot.interecagent_bridge.run_turn", side_effect=noisy_run_turn):
            with patch("sys.stdin", io.StringIO(payload)):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            RecBotTurnResult.from_dict(__import__("json").loads(stdout.getvalue())).assistant_message,
            "A recommendation.",
        )
        self.assertIn("noisy backend output", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
