import unittest

from recbot.types import (
    ChatMessage,
    NativeAction,
    RecBotRequest,
    RecBotTrace,
    RecBotTurnResult,
)


class RecBotTypesTest(unittest.TestCase):
    def test_request_round_trip_keeps_messages_and_metadata(self):
        request = RecBotRequest(
            conversation_id="episode_001",
            turn_id=2,
            messages=[
                ChatMessage(role="user", content="Can you recommend a movie?"),
                ChatMessage(role="assistant", content="What mood do you want?"),
                ChatMessage(role="user", content="Something tense but not horror."),
            ],
            metadata={"domain": "movie"},
        )

        restored = RecBotRequest.from_dict(request.to_dict())

        self.assertEqual(restored.conversation_id, "episode_001")
        self.assertEqual(restored.turn_id, 2)
        self.assertEqual(restored.latest_user_message, "Something tense but not horror.")
        self.assertEqual(restored.metadata["domain"], "movie")

    def test_turn_result_round_trip_keeps_native_action_and_trace(self):
        result = RecBotTurnResult(
            backend="interecagent",
            conversation_id="episode_001",
            turn_id=3,
            user_message="Something tense but not horror.",
            assistant_message="I recommend Aurora Station.",
            native_action=NativeAction(raw="Action: ToolExecutor\nAction Input: []"),
            trace=RecBotTrace(
                raw_tool_plan=[{"tool_name": "RankingTool", "input": "preference"}],
                raw_tool_outputs="ranked candidates",
                recommended_item_ids=["movie_fixture:aurora_station"],
            ),
        )

        restored = RecBotTurnResult.from_dict(result.to_dict())

        self.assertEqual(restored.backend, "interecagent")
        self.assertEqual(restored.native_action.raw, "Action: ToolExecutor\nAction Input: []")
        self.assertEqual(restored.trace.recommended_item_ids, ["movie_fixture:aurora_station"])

    def test_native_action_round_trip_keeps_raw_tool_plan(self):
        action = NativeAction(
            raw="Action: ToolExecutor\nAction Input: []",
            raw_tool_plan=[{"tool_name": "RankingTool", "input": "preference"}],
        )

        restored = NativeAction.from_dict(action.to_dict())

        self.assertEqual(restored.raw, "Action: ToolExecutor\nAction Input: []")
        self.assertEqual(
            restored.raw_tool_plan,
            [{"tool_name": "RankingTool", "input": "preference"}],
        )

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValueError):
            ChatMessage(role="bot", content="hello")

    def test_request_without_user_message_is_rejected(self):
        with self.assertRaises(ValueError):
            RecBotRequest(
                conversation_id="episode_001",
                turn_id=1,
                messages=[ChatMessage(role="assistant", content="hello")],
            )

    def test_request_rejects_invalid_turn_id(self):
        for turn_id in (-1, True):
            with self.subTest(turn_id=turn_id):
                with self.assertRaises(ValueError):
                    RecBotRequest(
                        conversation_id="episode_001",
                        turn_id=turn_id,
                        messages=[ChatMessage(role="user", content="hello")],
                    )

    def test_turn_result_rejects_invalid_turn_id(self):
        for turn_id in (-1, True):
            with self.subTest(turn_id=turn_id):
                with self.assertRaises(ValueError):
                    RecBotTurnResult(
                        backend="interecagent",
                        conversation_id="episode_001",
                        turn_id=turn_id,
                        user_message="hello",
                        assistant_message="hi",
                    )


if __name__ == "__main__":
    unittest.main()
