"""Platform collectors for computer-use system telemetry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """Collect OS-level signals for one snapshot phase."""

    @abstractmethod
    async def collect(self, environment: Any, *, phase: str) -> dict[str, Any]:
        """Return signal key-values for *phase* (baseline, final, step, ...)."""
