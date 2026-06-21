# platform_client.py — HTTP client for agents to interact with the shared platform service.
# Replaces OASIS's Channel-based async communication with synchronous HTTP calls.
# Each method maps to one platform endpoint and one OASIS action type.

from __future__ import annotations

from typing import Any

import requests


class PlatformClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def health(self) -> dict[str, Any]:
        resp = requests.get(f"{self._base_url}/health", timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def signup(self, agent_id: int, user_name: str, name: str, bio: str = "") -> dict[str, Any]:
        resp = requests.post(
            f"{self._base_url}/signup",
            json={"agent_id": agent_id, "user_name": user_name, "name": name, "bio": bio},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def action(self, user_id: int, action_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.post(
            f"{self._base_url}/action",
            json={"user_id": user_id, "action_type": action_type, "params": params or {}},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def refresh(self, user_id: int) -> list[dict[str, Any]]:
        result = self.action(user_id, "refresh", {})
        if result.get("success") and result.get("data"):
            return result["data"].get("posts", [])
        return []

    def create_post(self, user_id: int, content: str) -> dict[str, Any]:
        return self.action(user_id, "create_post", {"content": content})

    def like_post(self, user_id: int, post_id: int) -> dict[str, Any]:
        return self.action(user_id, "like_post", {"post_id": post_id})

    def repost(self, user_id: int, post_id: int) -> dict[str, Any]:
        return self.action(user_id, "repost", {"post_id": post_id})

    def follow(self, user_id: int, target_id: int) -> dict[str, Any]:
        return self.action(user_id, "follow", {"user_id": target_id})

    def do_nothing(self, user_id: int) -> dict[str, Any]:
        return self.action(user_id, "do_nothing", {})

    def get_state(self, agent_id: int) -> dict[str, Any]:
        resp = requests.get(f"{self._base_url}/state/{agent_id}", timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def get_stats(self) -> dict[str, Any]:
        resp = requests.get(f"{self._base_url}/stats", timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()
