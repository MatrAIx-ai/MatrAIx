import unittest

from recbot.native_contract import (
    assistant_message_from_native_output,
    build_native_action,
    extract_action_input,
    extract_final_answer,
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


if __name__ == "__main__":
    unittest.main()
