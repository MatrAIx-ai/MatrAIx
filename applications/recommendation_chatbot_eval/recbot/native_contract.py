from __future__ import annotations

import ast
import json
import re
from typing import Any

from recbot.types import NativeAction


_FINAL_ANSWER_PATTERN = re.compile(
    r"final\s+answer\s*\d*\s*:\s*(?P<answer>.*)",
    re.IGNORECASE | re.DOTALL,
)
_ACTION_INPUT_PATTERN = re.compile(
    r"action\s*\d*\s*:\s*.*?\n\s*action\s+input\s*\d*\s*:\s*(?P<input>.*)",
    re.IGNORECASE | re.DOTALL,
)


def extract_final_answer(raw_output: str) -> str | None:
    match = _FINAL_ANSWER_PATTERN.search(raw_output)
    if not match:
        return None
    return match.group("answer").strip()


def extract_action_input(raw_output: str) -> str | None:
    match = _ACTION_INPUT_PATTERN.search(raw_output)
    if not match:
        return None
    return match.group("input").strip()


def parse_action_input(action_input: str) -> Any:
    try:
        return json.loads(action_input)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(action_input)
    except (ValueError, SyntaxError):
        return action_input


def build_native_action(raw_output: str) -> NativeAction:
    raw = raw_output.strip()
    action_input = extract_action_input(raw)
    raw_tool_plan = parse_action_input(action_input) if action_input is not None else None
    return NativeAction(raw=raw, raw_tool_plan=raw_tool_plan)


def assistant_message_from_native_output(raw_output: str) -> str:
    final_answer = extract_final_answer(raw_output)
    if final_answer is not None:
        return final_answer
    return raw_output.strip()
