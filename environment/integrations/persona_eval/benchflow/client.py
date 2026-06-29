"""Small BenchFlow client boundary for PersonaEval runners.

The PersonaEval backend treats BenchFlow as an external execution runtime. This
module deliberately exposes only the operations the service layer needs:
create a typed run, wait for completion, and fetch named artifacts. Tests can
subclass :class:`BenchFlowClient` and override those methods without importing a
BenchFlow SDK or making network calls.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class BenchFlowRunError(RuntimeError):
    """Raised when a BenchFlow run cannot be created or completed."""


@dataclass(frozen=True)
class BenchFlowRun:
    """Minimal view of a BenchFlow run."""

    id: str
    status: str
    detail: dict[str, Any] | None = None


class BenchFlowClient:
    """HTTP client for a BenchFlow-compatible runner API.

    The default endpoint shape is intentionally plain:

    * ``POST /v1/runs`` with ``{"taskType": ..., "payload": ...}``
    * ``GET /v1/runs/{id}``
    * ``GET /v1/runs/{id}/artifacts/{name}``

    A real deployment can adapt this class if BenchFlow exposes a different
    path layout while keeping the runner contracts unchanged.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 2.0,
        max_wait_seconds: float = 1800.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("BENCHFLOW_API_URL") or "").rstrip(
            "/"
        )
        self.api_key = api_key if api_key is not None else os.environ.get(
            "BENCHFLOW_API_KEY"
        )
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_wait_seconds = max_wait_seconds

    def create_run(self, *, task_type: str, payload: dict[str, Any]) -> BenchFlowRun:
        """Create a BenchFlow run for a PersonaEval task type."""
        data = self._request_json(
            "POST",
            "/v1/runs",
            body={"taskType": task_type, "payload": payload},
        )
        return _run_from_payload(data)

    def wait_for_run(self, run_id: str) -> BenchFlowRun:
        """Poll until the run reaches a terminal status."""
        deadline = time.monotonic() + self.max_wait_seconds
        last = BenchFlowRun(id=run_id, status="unknown")
        while time.monotonic() <= deadline:
            last = _run_from_payload(self._request_json("GET", f"/v1/runs/{run_id}"))
            if last.status in {"succeeded", "done", "failed", "error", "cancelled"}:
                if last.status in {"failed", "error", "cancelled"}:
                    raise BenchFlowRunError(
                        "BenchFlow run {} ended with status {}".format(
                            run_id, last.status
                        )
                    )
                return last
            time.sleep(self.poll_interval)
        raise BenchFlowRunError(
            "BenchFlow run {} did not finish within {} seconds; last status {}".format(
                run_id, self.max_wait_seconds, last.status
            )
        )

    def get_artifact(self, run_id: str, name: str) -> Any:
        """Fetch one named artifact for a completed run."""
        return self._request_json("GET", f"/v1/runs/{run_id}/artifacts/{name}")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        if not self.base_url:
            raise BenchFlowRunError(
                "BENCHFLOW_API_URL is required when MATRIX_PERSONA_EVAL_RUNTIME=benchflow"
            )
        data = None
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BenchFlowRunError(
                "BenchFlow {} {} failed with HTTP {}: {}".format(
                    method, path, exc.code, detail
                )
            ) from exc
        except urllib.error.URLError as exc:
            raise BenchFlowRunError(
                "BenchFlow {} {} failed: {}".format(method, path, exc)
            ) from exc
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise BenchFlowRunError("BenchFlow returned invalid JSON") from exc
        return payload


def _run_from_payload(payload: Any) -> BenchFlowRun:
    if not isinstance(payload, dict):
        raise BenchFlowRunError("BenchFlow run response must be a JSON object")
    run_id = str(payload.get("id") or payload.get("runId") or "").strip()
    if not run_id:
        raise BenchFlowRunError("BenchFlow run response missing id")
    return BenchFlowRun(
        id=run_id,
        status=str(payload.get("status") or "unknown"),
        detail=dict(payload),
    )
