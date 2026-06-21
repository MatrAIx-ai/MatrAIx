# recsys.py — Recommendation system implementations matching OASIS's 4 algorithms.
# Controls what each agent sees in their feed. This is the information flow bottleneck
# that shapes emergent social behavior in the simulation.

from __future__ import annotations

import math
import random
from enum import Enum
from typing import Any

from environments.oasis.platform.database import Database


class RecSysType(Enum):
    RANDOM = "random"
    REDDIT = "reddit"
    TWITTER = "twitter"
    TWHIN = "twhin"


class RecSys:
    def __init__(self, db: Database, recsys_type: RecSysType = RecSysType.RANDOM, max_rec_posts: int = 50):
        self._db = db
        self._type = recsys_type
        self._max_rec_posts = max_rec_posts

    @property
    def recsys_type(self) -> RecSysType:
        return self._type

    def update_recommendations(self) -> int:
        users = self._db.get_all_users()
        posts = self._db.get_all_posts(limit=5000)

        if not users or not posts:
            self._db.set_recommendations([])
            return 0

        if self._type == RecSysType.RANDOM:
            recs = self._random_recs(users, posts)
        elif self._type == RecSysType.REDDIT:
            recs = self._reddit_hot_recs(users, posts)
        elif self._type == RecSysType.TWITTER:
            recs = self._twitter_recs(users, posts)
        elif self._type == RecSysType.TWHIN:
            recs = self._twitter_recs(users, posts)
        else:
            recs = self._random_recs(users, posts)

        self._db.set_recommendations(recs)
        return len(recs)

    def _random_recs(self, users: list[dict], posts: list[dict]) -> list[tuple[int, int]]:
        recs = []
        post_ids = [p["post_id"] for p in posts]
        for user in users:
            user_id = user["user_id"]
            sample_size = min(self._max_rec_posts, len(post_ids))
            selected = random.sample(post_ids, sample_size)
            for pid in selected:
                recs.append((user_id, pid))
        return recs

    def _reddit_hot_recs(self, users: list[dict], posts: list[dict]) -> list[tuple[int, int]]:
        scored_posts = []
        for post in posts:
            likes = post.get("num_likes", 0)
            dislikes = post.get("num_dislikes", 0)
            score = likes - dislikes
            sign = 1 if score > 0 else (-1 if score < 0 else 0)
            order = math.log10(max(abs(score), 1))

            created_at = post.get("created_at", "")
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                epoch_seconds = dt.timestamp()
            except (ValueError, TypeError):
                epoch_seconds = 0

            hot_score = sign * order + epoch_seconds / 45000.0
            scored_posts.append((post["post_id"], hot_score))

        scored_posts.sort(key=lambda x: x[1], reverse=True)
        top_post_ids = [pid for pid, _ in scored_posts[: self._max_rec_posts]]

        recs = []
        for user in users:
            for pid in top_post_ids:
                recs.append((user["user_id"], pid))
        return recs

    def _twitter_recs(self, users: list[dict], posts: list[dict]) -> list[tuple[int, int]]:
        user_bios = {u["user_id"]: (u.get("bio") or u.get("name", "")) for u in users}
        post_texts = {p["post_id"]: p.get("content", "") for p in posts}
        post_authors = {p["post_id"]: p["user_id"] for p in posts}

        recs = []
        post_ids = list(post_texts.keys())

        for user in users:
            user_id = user["user_id"]
            user_bio_words = set(user_bios.get(user_id, "").lower().split())

            if not user_bio_words:
                sample_size = min(self._max_rec_posts, len(post_ids))
                for pid in random.sample(post_ids, sample_size):
                    recs.append((user_id, pid))
                continue

            scored = []
            for pid in post_ids:
                if post_authors.get(pid) == user_id:
                    continue
                post_words = set(post_texts[pid].lower().split())
                if not post_words:
                    continue
                overlap = len(user_bio_words & post_words)
                score = overlap / max(len(user_bio_words), 1)
                scored.append((pid, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            for pid, _ in scored[: self._max_rec_posts]:
                recs.append((user_id, pid))

        return recs
