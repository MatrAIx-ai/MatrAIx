from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from persona.tools.annotation_package.core import canonical_json, sha256_text


SOURCE = "amazon_reviews_2023"
FOLD_SEPARATOR = "\n\n"
FOLD_TRUNCATION_MARKER = "[fold truncated]"


def _load_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object row")
            yield row


def _timestamp(review: dict[str, Any]) -> int | None:
    value = review.get("timestamp")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sorted_reviews(reviews: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(idx, dict(review)) for idx, review in enumerate(reviews)]
    indexed.sort(
        key=lambda item: (
            _timestamp(item[1]) is None,
            _timestamp(item[1]) or 0,
            item[0],
        )
    )
    return [review for _idx, review in indexed]


def _spread_across_time(
    reviews: list[dict[str, Any]],
    max_reviews: int,
) -> list[dict[str, Any]]:
    if len(reviews) <= max_reviews:
        return reviews
    if max_reviews == 1:
        return [reviews[len(reviews) // 2]]
    last = len(reviews) - 1
    indexes = [round(pos * last / (max_reviews - 1)) for pos in range(max_reviews)]
    return [reviews[index] for index in indexes]


def _compact_text(value: Any, max_chars: int) -> str:
    text = "" if value is None else " ".join(str(value).split())
    if len(text) <= max_chars:
        return text
    if max_chars <= 16:
        return text[:max_chars]
    return text[: max_chars - 15].rstrip() + " ... [truncated]"


def _first_nonblank(
    review: dict[str, Any],
    keys: tuple[str, ...],
    default: str = "",
) -> str:
    for key in keys:
        value = review.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _has_review_evidence(review: dict[str, Any]) -> bool:
    return bool(
        _first_nonblank(review, ("title", "product_title", "text", "review_text"))
    )


def _render_review(
    review: dict[str, Any], *, rendered_review_id: str, max_review_text_chars: int
) -> str:
    category = review.get("category") or review.get("source_category") or "Unknown"
    title = _first_nonblank(review, ("title", "product_title"), "(untitled)")
    verified = review.get("verified_purchase", review.get("verified", "unknown"))
    helpful_vote = review.get("helpful_vote", review.get("helpful_votes", 0))
    review_text = _first_nonblank(review, ("text", "review_text"))
    return "\n".join(
        [
            f"[{rendered_review_id}]",
            f"date: {review.get('date') or 'unknown'}",
            f"category: {category}",
            f"rating: {review.get('rating', 'unknown')}",
            f"title: {title}",
            f"verified: {verified}",
            f"helpful_vote: {helpful_vote}",
            f"text: {_compact_text(review_text, max_review_text_chars)}",
        ]
    )


def _assign_folds(
    reviews: list[dict[str, Any]], *, effective_cv_folds: int
) -> list[list[tuple[str, dict[str, Any]]]]:
    folds: list[list[tuple[str, dict[str, Any]]]] = [
        [] for _ in range(effective_cv_folds)
    ]
    for idx, review in enumerate(reviews):
        rendered_id = f"r{idx + 1:04d}"
        folds[idx % effective_cv_folds].append((rendered_id, review))
    return folds


def _render_fold(
    fold_id: int,
    effective_cv_folds: int,
    reviews: list[tuple[str, dict[str, Any]]],
    *,
    max_review_text_chars: int,
) -> str:
    lines = [f"=== Fold {fold_id}/{effective_cv_folds} ==="]
    for rendered_id, review in reviews:
        lines.append(
            _render_review(
                review,
                rendered_review_id=rendered_id,
                max_review_text_chars=max_review_text_chars,
            )
        )
    return "\n\n".join(lines)


def _profile_text(fold_texts: list[dict[str, Any]]) -> str:
    return FOLD_SEPARATOR.join(
        str(fold["profile_text"]) for fold in fold_texts if fold["profile_text"]
    )


def _limit_profile_text(
    fold_texts: list[dict[str, Any]],
    max_chars: int,
) -> list[dict[str, Any]]:
    if len(_profile_text(fold_texts)) <= max_chars:
        return fold_texts
    limited: list[dict[str, Any]] = []
    used = 0
    for fold in fold_texts:
        fold = dict(fold)
        separator = len(FOLD_SEPARATOR) if used else 0
        remaining = max_chars - used - separator
        if remaining <= 0:
            fold["profile_text"] = ""
        elif len(str(fold["profile_text"])) > remaining:
            marker = "\n" + FOLD_TRUNCATION_MARKER
            fold["profile_text"] = (
                str(fold["profile_text"])[: max(0, remaining - len(marker))].rstrip()
                + marker
            )
        used += separator + len(str(fold["profile_text"]))
        limited.append(fold)
    return limited


def amazon_input_payload(task: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in task.items() if key != "input_sha256"}


def build_amazon_task(
    row: dict[str, Any],
    *,
    global_idx: int,
    cv_folds: int,
    min_support_folds: int,
    max_reviews_per_user: int,
    max_review_text_chars: int,
    max_profile_text_chars: int,
) -> dict[str, Any]:
    user_id = str(row.get("user_id") or row.get("reviewer_id") or f"user_{global_idx}")
    raw_reviews = row.get("reviews")
    if not isinstance(raw_reviews, list):
        raise ValueError(f"user {user_id}: reviews must be a list")
    reviews = [
        dict(review)
        for review in raw_reviews
        if isinstance(review, dict) and _has_review_evidence(review)
    ]
    reviews = _spread_across_time(_sorted_reviews(reviews), max_reviews_per_user)
    effective_cv_folds = min(cv_folds, len(reviews))
    if effective_cv_folds < 2:
        raise ValueError(f"user {user_id}: at least 2 usable reviews are required")

    folds = _assign_folds(reviews, effective_cv_folds=effective_cv_folds)
    fold_texts = [
        {
            "fold_id": idx + 1,
            "profile_text": _render_fold(
                idx + 1,
                effective_cv_folds,
                fold_reviews,
                max_review_text_chars=max_review_text_chars,
            ),
        }
        for idx, fold_reviews in enumerate(folds)
    ]
    fold_texts = _limit_profile_text(fold_texts, max_profile_text_chars)
    task = {
        "global_idx": global_idx,
        "task_id": f"{SOURCE}:{user_id}",
        "qid": f"amazon_user:{user_id}",
        "title": f"Amazon reviewer {user_id}",
        "source_url": "",
        "profile_text": _profile_text(fold_texts),
        "source": SOURCE,
        "user_id": user_id,
        "review_count": len(reviews),
        "categories": sorted(
            {str(review.get("category") or "Unknown") for review in reviews}
        ),
        "cv_folds": cv_folds,
        "effective_cv_folds": effective_cv_folds,
        "min_support_folds": min(min_support_folds, effective_cv_folds),
        "cv_fold_texts": fold_texts,
    }
    task["input_sha256"] = sha256_text(canonical_json(amazon_input_payload(task)))
    return task


def load_amazon_tasks(
    user_histories_path: Path,
    *,
    range_start: int,
    range_end: int,
    cv_folds: int = 3,
    min_support_folds: int = 2,
    max_reviews_per_user: int = 90,
    max_review_text_chars: int = 900,
    max_profile_text_chars: int = 70_000,
) -> list[dict[str, Any]]:
    rows = list(_load_jsonl(user_histories_path))
    selected = rows[range_start:range_end]
    expected_count = range_end - range_start
    if len(selected) != expected_count:
        raise ValueError(
            f"range [{range_start}, {range_end}) expected {expected_count} rows, "
            f"got {len(selected)}"
        )
    return [
        build_amazon_task(
            row,
            global_idx=range_start + offset,
            cv_folds=cv_folds,
            min_support_folds=min_support_folds,
            max_reviews_per_user=max_reviews_per_user,
            max_review_text_chars=max_review_text_chars,
            max_profile_text_chars=max_profile_text_chars,
        )
        for offset, row in enumerate(selected)
    ]
