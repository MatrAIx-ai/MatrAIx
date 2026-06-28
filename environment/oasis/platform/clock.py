# clock.py — Sandbox time management matching OASIS's Clock class.
# Twitter mode uses discrete integer time_steps.
# Reddit mode uses time_transfer with magnification factor k (default 60x).

from __future__ import annotations

from datetime import datetime


class Clock:
    def __init__(self, k: int = 60):
        self.real_start_time = datetime.now()
        self.k = k
        self.time_step = 0

    def time_transfer(self, now_time: datetime, start_time: datetime) -> datetime:
        time_diff = now_time - self.real_start_time
        adjusted_diff = self.k * time_diff
        adjusted_time = start_time + adjusted_diff
        return adjusted_time

    def get_time_step(self) -> str:
        return str(self.time_step)

    def advance(self) -> int:
        self.time_step += 1
        return self.time_step
