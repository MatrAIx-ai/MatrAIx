"""Offline integration tests for the harvest runner.

Monkeypatches the network layer so the checkpoint/resume/backoff logic —
the parts that must survive a multi-hour unattended run — are exercised
without touching Amazon.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_TASK_DIR = Path(__file__).resolve().parent.parent
for _p in (_TASK_DIR / "scripts", _TASK_DIR / "tests"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import harvest as harvest_mod  # noqa: E402
from scrape_amazon import BlockedError  # noqa: E402
from test_scraper import _FULL_PAGE, _PO_TABLE, _REVIEWS, _TITLE, _page  # noqa: E402


def _write_candidates(path: Path, n: int) -> None:
    candidates = [
        {
            "asin": f"B00000000{i}",
            "url": f"https://www.amazon.com/dp/B00000000{i}",
            "category": "kitchen",
        }
        for i in range(n)
    ]
    path.write_text(json.dumps({"candidates": candidates, "done_pages": []}))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harvest_mod.time, "sleep", lambda _: None)


def test_harvest_accepts_and_checkpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidates = tmp_path / "candidates.json"
    _write_candidates(candidates, 3)
    monkeypatch.setattr(
        harvest_mod, "fetch_page", lambda url, session=None: _FULL_PAGE
    )

    harvest_mod.harvest(candidates, tmp_path / "harvest", target=2)

    results = _read_jsonl(tmp_path / "harvest.jsonl")
    assert len(results) == 2
    assert all(len(r["attributes"]) >= 5 for r in results)
    assert all(r["original_price"] == 99.00 for r in results)


def test_harvest_resumes_from_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidates = tmp_path / "candidates.json"
    _write_candidates(candidates, 3)
    fetched: list[str] = []

    def fake_fetch(url: str, session=None) -> str:
        fetched.append(url)
        return _FULL_PAGE

    monkeypatch.setattr(harvest_mod, "fetch_page", fake_fetch)

    harvest_mod.harvest(candidates, tmp_path / "harvest", target=2)
    assert len(fetched) == 2

    # Rerun: the two done ASINs are skipped, only the third is fetched.
    harvest_mod.harvest(candidates, tmp_path / "harvest", target=3)
    assert len(fetched) == 3
    assert len(set(fetched)) == 3
    assert len(_read_jsonl(tmp_path / "harvest.jsonl")) == 3


def test_harvest_recovers_from_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidates = tmp_path / "candidates.json"
    _write_candidates(candidates, 1)
    calls = {"n": 0}

    def flaky_fetch(url: str, session=None) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise BlockedError("captcha")
        return _FULL_PAGE

    monkeypatch.setattr(harvest_mod, "fetch_page", flaky_fetch)

    harvest_mod.harvest(candidates, tmp_path / "harvest", target=1)

    assert calls["n"] == 2  # blocked once, retried inline after backoff
    assert len(_read_jsonl(tmp_path / "harvest.jsonl")) == 1
    assert _read_jsonl(tmp_path / "harvest.rejects.jsonl") == []


def test_harvest_rejects_thin_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidates = tmp_path / "candidates.json"
    _write_candidates(candidates, 1)
    # Page with title+reviews but no attributes and no price.
    monkeypatch.setattr(
        harvest_mod,
        "fetch_page",
        lambda url, session=None: _page(_TITLE, _REVIEWS),
    )

    harvest_mod.harvest(candidates, tmp_path / "harvest", target=1)

    assert _read_jsonl(tmp_path / "harvest.jsonl") == []
    rejects = _read_jsonl(tmp_path / "harvest.rejects.jsonl")
    assert len(rejects) == 1
    assert "too_few_attributes" in rejects[0]["reason"]


def test_harvest_retries_degraded_template_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A page with everything but the buybox price is retried at the end
    of the run (degraded post-block template), then accepted if the
    retry render includes the price."""
    candidates = tmp_path / "candidates.json"
    _write_candidates(candidates, 1)
    calls = {"n": 0}
    degraded = _page(_TITLE, _REVIEWS, _PO_TABLE)  # no price section

    def improving_fetch(url: str, session=None) -> str:
        calls["n"] += 1
        return degraded if calls["n"] == 1 else _FULL_PAGE

    monkeypatch.setattr(harvest_mod, "fetch_page", improving_fetch)

    harvest_mod.harvest(candidates, tmp_path / "harvest", target=1)

    assert calls["n"] == 2
    results = _read_jsonl(tmp_path / "harvest.jsonl")
    assert len(results) == 1
    assert results[0]["original_price"] == 99.00
