from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import Any, Iterable

import numpy as np


class SemanticProfileRankingTool:
    """RecAI-compatible ranking tool without a catalog-specific UniRec checkpoint."""

    def __init__(
        self,
        name: str,
        desc: str,
        item_corups,
        buffer,
        rec_num: int | None = None,
        request_weight: float = 0.15,
        profile_weight: float = 0.75,
        popularity_weight: float = 0.10,
        unwanted_penalty: float = 1.0,
    ) -> None:
        self.name = name
        self.desc = desc
        self.item_corups = item_corups
        self.buffer = buffer
        self.rec_num = rec_num
        self.request_weight = request_weight
        self.profile_weight = profile_weight
        self.popularity_weight = popularity_weight
        self.unwanted_penalty = unwanted_penalty
        self._mode = "accuracy"

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode: str) -> None:
        self._mode = mode

    def run(self, inputs: str) -> str:
        try:
            parsed = json.loads(inputs)
        except json.JSONDecodeError:
            output = f"{self.name}: Input format error."
            self.buffer.track(self.name, inputs, output)
            return output

        candidates = self.buffer.get()
        info = f"Before {self.name}: There are {len(candidates)} candidates in buffer. "
        if not candidates:
            output = info + "Stop execution. \n"
            self.buffer.track(self.name, parsed, output)
            return output

        schema = parsed.get("schema", "popularity")
        prefer_ids = self._titles_to_ids(parsed.get("prefer", []))
        unwanted_ids = self._titles_to_ids(parsed.get("unwanted", []))

        if schema not in {"popularity", "preference", "similarity"}:
            schema = "popularity"
            info += "Ranking schema switched to 'popularity'. \n"
        if prefer_ids:
            schema = "preference"
            info += f"{self.name}: ranking schema switch to 'preference' because 'prefer' info is given. \n"
        if schema == "preference" and not prefer_ids:
            schema = "popularity"
            info += f"{self.name}: ranking schema switch to 'popularity' because 'prefer' info is not given. \n"
        if schema == "similarity" and self.buffer.similarity is None:
            schema = "popularity"
            info += f"{self.name}: ranking schema switch to 'popularity' because similarity scores have not been calculated. \n"

        rec_count = min(len(candidates), self.rec_num or len(candidates))
        if schema == "similarity":
            ranked = self._rank_by_x(candidates, self.buffer.similarity, rec_count, unwanted_ids)
            output = (
                info
                + f"{self.name}: Items are ranked according to the similarity with seed items. "
                "The ranked item ids are stored in buffer and are visible to all tools. \n"
            )
        elif schema == "preference":
            ranked = self._rank_by_semantic_profile(
                candidates,
                prefer_ids,
                unwanted_ids,
                rec_count,
            )
            output = (
                info
                + f"{self.name}: Items are ranked according to a semantic profile substitute for the native recommender checkpoint. "
                "The ranked item ids are stored in buffer and are visible to all tools. \n"
            )
        else:
            ranked = self._rank_by_pop(candidates, rec_count, unwanted_ids)
            output = (
                info
                + f"{self.name}: Items are ranked according to their popularities. "
                "The ranked item ids are stored in buffer and are visible to all tools. \n"
            )

        self.buffer.push(self.name, ranked)
        self.buffer.track(self.name, parsed, output)
        return output

    def _titles_to_ids(self, titles: Any) -> list[int]:
        if isinstance(titles, str):
            titles = [titles]
        if not isinstance(titles, list) or not titles:
            return []
        try:
            matched_titles = self.item_corups.fuzzy_match(titles, "title")
            info = self.item_corups.convert_title_2_info(matched_titles, col_names="id")
            ids = info["id"]
        except Exception:
            return []
        if isinstance(ids, (int, np.integer)):
            return [int(ids)]
        return [int(item_id) for item_id in ids]

    def _rank_by_pop(
        self,
        candidates: list[int],
        rec_count: int,
        masked_items: list[int],
    ) -> list[int]:
        popularity = self._popularity(candidates)
        return self._rank_by_x(candidates, popularity, rec_count, masked_items)

    def _rank_by_x(
        self,
        candidates: list[int],
        scores: Iterable[float],
        rec_count: int,
        masked_items: list[int],
    ) -> list[int]:
        masked = set(masked_items)
        scored = [
            (candidate, float(score))
            for candidate, score in zip(candidates, scores)
            if candidate not in masked
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [candidate for candidate, _ in scored[:rec_count]]

    def _rank_by_semantic_profile(
        self,
        candidates: list[int],
        prefer_ids: list[int],
        unwanted_ids: list[int],
        rec_count: int,
    ) -> list[int]:
        masked = set(prefer_ids + unwanted_ids)
        candidate_text = self._item_text(candidates)
        prefer_vector = _mean_vector(self._item_text(prefer_ids).values())
        unwanted_vector = _mean_vector(self._item_text(unwanted_ids).values())
        request_vector = _text_vector(os.environ.get("MATRAIX_CURRENT_USER_REQUEST", ""))
        popularity = self._normalized_popularity(candidates)

        scored: list[tuple[int, float]] = []
        for candidate in candidates:
            if candidate in masked:
                continue
            vector = _text_vector(candidate_text.get(candidate, ""))
            profile_score = _cosine(vector, prefer_vector)
            request_score = _cosine(vector, request_vector)
            unwanted_score = _cosine(vector, unwanted_vector)
            score = (
                self.profile_weight * profile_score
                + self.request_weight * request_score
                + self.popularity_weight * popularity.get(candidate, 0.0)
                - self.unwanted_penalty * unwanted_score
            )
            scored.append((candidate, score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [candidate for candidate, _ in scored[:rec_count]]

    def _item_text(self, item_ids: list[int]) -> dict[int, str]:
        if not item_ids:
            return {}
        for columns in (
            ["title", "display_text", "tags", "description"],
            ["title", "display_text", "tags"],
            ["title", "description"],
            ["title"],
        ):
            try:
                info = self.item_corups.convert_id_2_info(item_ids, col_names=columns)
                return {
                    item_id: " ".join(
                        str(info[column][index])
                        for column in columns
                        if info.get(column) and info[column][index] is not None
                    )
                    for index, item_id in enumerate(item_ids)
                }
            except Exception:
                continue
        return {item_id: str(item_id) for item_id in item_ids}

    def _popularity(self, item_ids: list[int]) -> list[float]:
        try:
            info = self.item_corups.convert_id_2_info(item_ids, col_names=["visited_num"])
            return [math.log(float(value) + 1.0) for value in info["visited_num"]]
        except Exception:
            return [1.0 for _ in item_ids]

    def _normalized_popularity(self, item_ids: list[int]) -> dict[int, float]:
        scores = self._popularity(item_ids)
        if not scores:
            return {}
        max_score = max(scores)
        if max_score <= 0:
            return {item_id: 0.0 for item_id in item_ids}
        return {item_id: score / max_score for item_id, score in zip(item_ids, scores)}


def _mean_vector(texts: Iterable[str]) -> Counter[str]:
    merged: Counter[str] = Counter()
    count = 0
    for text in texts:
        merged.update(_text_vector(text))
        count += 1
    if count <= 1:
        return merged
    for key in list(merged):
        merged[key] = merged[key] / count
    return merged


def _text_vector(text: str) -> Counter[str]:
    return Counter(_tokenize(text))


def _tokenize(text: str) -> Iterable[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in overlap)
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left.values()))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return float(numerator / (left_norm * right_norm))
