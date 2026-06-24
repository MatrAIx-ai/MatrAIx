"""Tests for Docker/Linux CUA submission materialization."""

from matraix.agents.persona.cua_submission import (
    extract_book_interest_from_trajectory,
    extract_ecommerce_interaction_from_trajectory,
)


def test_extract_book_interest_from_done_action() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "done",
                            "result": (
                                '{"title": "Sapiens", "price_gbp": "£54.23", '
                                '"interested": true, "reason": "Great systems lens."}'
                            ),
                        },
                    }
                ],
            }
        ]
    }
    payload = extract_book_interest_from_trajectory(trajectory)
    assert payload == {
        "title": "Sapiens",
        "price_gbp": "£54.23",
        "interested": True,
        "reason": "Great systems lens.",
    }


def test_extract_book_interest_from_message_fence() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "message": (
                    "Done.\n```json\n"
                    '{"title": "A Light in the Attic", "price_gbp": "£51.77", '
                    '"interested": false, "reason": "Not my genre right now."}\n'
                    "```"
                ),
            }
        ]
    }
    payload = extract_book_interest_from_trajectory(trajectory)
    assert payload["title"] == "A Light in the Attic"
    assert payload["interested"] is False


def test_extract_book_interest_prefers_latest_submission() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "done",
                            "result": (
                                '{"title": "Old", "price_gbp": "£1.00", '
                                '"interested": true, "reason": "draft choice"}'
                            ),
                        },
                    }
                ],
            },
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "answer",
                            "text": (
                                '{"title": "Final", "price_gbp": "£2.00", '
                                '"interested": true, "reason": "final choice"}'
                            ),
                        },
                    }
                ],
            },
        ]
    }
    payload = extract_book_interest_from_trajectory(trajectory)
    assert payload["title"] == "Final"


def test_extract_ecommerce_interaction_from_done_action() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "done",
                            "result": (
                                '{"selected_product_id": "desk-002", '
                                '"selected_product_name": "FocusDesk Pro", '
                                '"need_satisfaction": 8, "ease_of_use": 7, '
                                '"overall_experience_rating": 8, '
                                '"reason": "The comparison page made the tradeoffs clear."}'
                            ),
                        },
                    }
                ],
            }
        ]
    }

    payload = extract_ecommerce_interaction_from_trajectory(trajectory)

    assert payload == {
        "selected_product_id": "desk-002",
        "selected_product_name": "FocusDesk Pro",
        "need_satisfaction": 8,
        "ease_of_use": 7,
        "overall_experience_rating": 8,
        "reason": "The comparison page made the tradeoffs clear.",
    }


def test_extract_ecommerce_interaction_rejects_boolean_scores() -> None:
    trajectory = {
        "steps": [
            {
                "source": "agent",
                "tool_calls": [
                    {
                        "function_name": "computer_action",
                        "arguments": {
                            "type": "done",
                            "result": (
                                '{"selected_product_id": "desk-002", '
                                '"selected_product_name": "FocusDesk Pro", '
                                '"need_satisfaction": true, "ease_of_use": 7, '
                                '"overall_experience_rating": 8, '
                                '"reason": "The comparison page made the tradeoffs clear."}'
                            ),
                        },
                    }
                ],
            }
        ]
    }

    assert extract_ecommerce_interaction_from_trajectory(trajectory) is None
