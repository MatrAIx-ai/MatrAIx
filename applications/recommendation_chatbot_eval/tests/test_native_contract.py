import unittest

from recbot.native_contract import (
    MAX_ACTION_INPUT_CHARS,
    assistant_message_from_native_output,
    build_native_action,
    extract_action_input,
    extract_final_answer,
    parse_action_input,
)


class NativeContractTest(unittest.TestCase):
    def test_extract_final_answer(self):
        raw = "Question: Do I need tools?\nFinal Answer: What kind of movie mood do you want?"

        self.assertEqual(
            extract_final_answer(raw),
            "What kind of movie mood do you want?",
        )
        self.assertEqual(
            assistant_message_from_native_output(raw),
            "What kind of movie mood do you want?",
        )

    def test_extract_action_input(self):
        raw = (
            "Question: Do I need tools?\n"
            "Action: ToolExecutor\n"
            "Action Input: [{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]"
        )

        self.assertEqual(
            extract_action_input(raw),
            "[{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]",
        )

    def test_build_native_action_parses_json_plan_when_possible(self):
        raw = (
            "Action: ToolExecutor\n"
            "Action Input: [{\"tool_name\": \"MapTool\", \"input\": \"5\"}]"
        )

        native_action = build_native_action(raw)

        self.assertEqual(native_action.raw, raw)
        self.assertEqual(native_action.raw_tool_plan, [{"tool_name": "MapTool", "input": "5"}])

    def test_build_native_action_keeps_unparsed_plan_string(self):
        raw = "Action: ToolExecutor\nAction Input: not-json"

        native_action = build_native_action(raw)

        self.assertEqual(native_action.raw_tool_plan, "not-json")

    def test_build_native_action_preserves_raw_whitespace(self):
        raw = "\n  Action: ToolExecutor\nAction Input: []  \n"

        native_action = build_native_action(raw)

        self.assertEqual(native_action.raw, raw)

    def test_extract_numbered_action_input(self):
        raw = (
            "Action 1: ToolExecutor\n"
            "Action 1 Input 1: [{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]"
        )

        self.assertEqual(
            extract_action_input(raw),
            "[{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]",
        )

    def test_action_input_stops_before_observation(self):
        raw = (
            "Action: ToolExecutor\n"
            "Action Input: [{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]\n"
            "Observation: done"
        )

        native_action = build_native_action(raw)

        self.assertEqual(
            extract_action_input(raw),
            "[{\"tool_name\": \"RankingTool\", \"input\": \"preference\"}]",
        )
        self.assertEqual(
            native_action.raw_tool_plan,
            [{"tool_name": "RankingTool", "input": "preference"}],
        )

    def test_parse_action_input_returns_oversized_input_unchanged(self):
        action_input = "[" + (" " * MAX_ACTION_INPUT_CHARS) + "]"

        self.assertIs(parse_action_input(action_input), action_input)


if __name__ == "__main__":
    unittest.main()
