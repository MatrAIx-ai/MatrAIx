"""Bridge iOS CUA `done` submissions to on-host decision.json for verifiers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from matraix.agents.persona.cua_submission import (
    extract_ios_decision_from_trajectory,
    materialize_json_file,
)

__all__ = [
    "extract_ios_decision_from_trajectory",
    "materialize_ios_decision_file",
    "IOS_SUBMISSION_INSTRUCTION_FOOTER",
]

IOS_SUBMISSION_INSTRUCTION_FOOTER = """

## How to submit (required)

You have a limited step budget. After reviewing **one** app's notifications, **stop navigating** and call the **done** tool:

- `success`: `true`
- `message`: your JSON on one line, for example:
  `{"keep_notifications_on": true, "app_reviewed": "Mail", "reason": "..."}`

Harbor scores from this JSON. If you run out of steps without calling **done**, the trial fails.
"""


async def materialize_ios_decision_file(
    environment: Any,
    logs_dir: Path,
    *,
    output_path: str = "/tmp/matraix-ios-notification-preferences/decision.json",
    logger: Any | None = None,
) -> bool:
    """Write decision.json on the simulator host from trajectory `done` tool output."""
    return await materialize_json_file(
        environment,
        logs_dir,
        extractor=extract_ios_decision_from_trajectory,
        output_path=output_path,
        logger=logger,
        log_label="ios submission",
    )
