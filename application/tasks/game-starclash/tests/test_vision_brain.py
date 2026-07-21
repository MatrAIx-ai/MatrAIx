"""Unit tests for the vision browser-use brain (scripts/vision_brain.py).

Dev/CI unit tests for --brain vision, kept separate from the harness verifier
(tests/test_state.py). Like test_bots.py they import the scripts package
directly rather than reading run artifacts.

The BrowserVisionBrain lazily imports `anthropic` + `playwright` only inside
__init__, and isolates its one real network call in `_ask_vision_model` and
its browser lifecycle in `_ensure_browser` precisely so both can be replaced
in tests. These tests therefore exercise the real decision plumbing - the
per-turn context brief (_context_note), the screenshot->primitive->execute
loop (_run_vision_loop), the reasoning threading, and the defensive
sanitizer - WITHOUT an API key, a network, or a browser. What they cannot
cover is how a real vision model behaves given the screenshot + brief; that
needs a live --brain vision run.
"""

import os
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import vision_brain  # noqa: E402
from vision_brain import BrowserVisionBrain  # noqa: E402

CARD_TYPES = ("Rock", "Paper", "Scissors")


# ---------------------------------------------------------------------------
# Test doubles.
# ---------------------------------------------------------------------------


class _FakePage:
    """Minimal stand-in for a Playwright Page. Records clicks/typed text and
    returns a scripted window.__lastAction from evaluate()."""

    def __init__(self, last_action):
        self._last_action = last_action
        self.clicks = []
        self.typed = []
        self.content_calls = 0

    def set_content(self, html, timeout=None):
        self.content_calls += 1

    def screenshot(self, timeout=None):
        return b"FAKE_PNG_BYTES"

    def evaluate(self, js):
        return self._last_action

    class _Mouse:
        def __init__(self, outer):
            self._outer = outer

        def click(self, x, y):
            self._outer.clicks.append((x, y))

    class _Keyboard:
        def __init__(self, outer):
            self._outer = outer

        def type(self, text):
            self._outer.typed.append(text)

    @property
    def mouse(self):
        return _FakePage._Mouse(self)

    @property
    def keyboard(self):
        return _FakePage._Keyboard(self)


def _make_brain(primitives, last_action, monkeypatch):
    """Build a BrowserVisionBrain WITHOUT running __init__ (which needs the
    anthropic/playwright imports), wire in a fake page + scripted model.

    `primitives` is the list of primitive dicts the model "returns" across the
    step loop; `last_action` is what window.__lastAction reads back at the end.
    """
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    brain._last_reasoning = None
    page = _FakePage(last_action)
    brain._page = page
    brain._ensure_browser = lambda: None
    # render_observation_html is heavy (inlines art); stub it out.
    monkeypatch.setattr(vision_brain, "render_observation_html", lambda obs: "<html></html>")

    seen_notes = []
    calls = {"n": 0}

    def fake_ask(screenshot_bytes, step_history, context_note=""):
        seen_notes.append(context_note)
        i = calls["n"]
        calls["n"] += 1
        return primitives[i] if i < len(primitives) else {"type": "done"}

    brain._ask_vision_model = fake_ask
    return brain, page, seen_notes


# ---------------------------------------------------------------------------
# Observation fixtures (mirror observations.build_observation shape).
# ---------------------------------------------------------------------------


def _obs_free(challengeable=True):
    menu_actions = ["say", "wait", "move"]
    if challengeable:
        menu_actions += ["challenge", "private_message"]
    return {
        "self": {"id": "0229", "display_name": "Kade", "stars": 3, "x": 10.0, "y": 10.0,
                 "hand": ["Rock", "Paper", "Scissors", "Rock"]},
        "arena_roster": [
            {"id": "0229", "is_self": True, "x": 10, "y": 10, "eliminated": False},
            {"id": "0052", "is_self": False, "x": 11, "y": 10.5, "eliminated": False,
             "short_name": "Arlo", "display_name": "Arlo Rowan"},
            {"id": "0666", "is_self": False, "x": 18, "y": 2, "eliminated": False,
             "short_name": "Blaze", "display_name": "Blaze Hawke"},
        ],
        "pending_challenge_from": None,
        "action_menu": {
            "actions": menu_actions,
            "challengeable_targets": ["0052"] if challengeable else [],
            "private_message_targets": ["0052"] if challengeable else [],
            "movable_bounds": {"max_distance": 2, "room_width": 20, "room_height": 20},
        },
    }


def _obs_play_card():
    return {
        "self": {"id": "0229", "stars": 3, "x": 5, "y": 5, "hand": ["Rock", "Scissors"]},
        "arena_roster": [], "pending_challenge_from": None,
        "action_menu": {"actions": ["play_card"], "available_cards": ["Rock", "Scissors"],
                        "private_message_targets": ["0052"]},
    }


def _obs_challenge_response():
    return {
        "self": {"id": "0229", "stars": 3, "x": 5, "y": 5, "hand": ["Rock", "Paper"]},
        "arena_roster": [],
        "pending_challenge_from": {"id": "0052", "display_name": "Arlo Rowan"},
        "action_menu": {"actions": ["accept", "decline"], "private_message_targets": ["0052"]},
    }


# ---------------------------------------------------------------------------
# 1. _context_note: correct brief per sub-step.
# ---------------------------------------------------------------------------


def test_context_note_free_action_with_target_explains_arm_then_click():
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    note = brain._context_note(_obs_free(challengeable=True))
    # Names the game + goal, the nearest challengeable target, and the two-step
    # DUEL interaction (the crux of the passive-vision bug).
    assert "Starclash" in note
    assert "0052" in note  # nearest challengeable target id surfaced
    assert "DUEL" in note
    assert "MOVES you" in note  # warns that a plain click just moves


def test_context_note_free_action_no_target_points_toward_approach():
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    note = brain._context_note(_obs_free(challengeable=False))
    assert "No one is close enough to duel" in note
    assert "MOVE" in note
    # Points at the nearest opponent so the model has a direction to head.
    assert "Arlo" in note or "Blaze" in note


def test_context_note_play_card_lists_available_cards():
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    note = brain._context_note(_obs_play_card())
    assert "play one card" in note
    assert "Rock" in note and "Scissors" in note


def test_context_note_challenge_response_names_challenger():
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    note = brain._context_note(_obs_challenge_response())
    assert "Arlo Rowan" in note
    assert "ACCEPT" in note and "DECLINE" in note


def test_context_note_never_leaks_opponent_hidden_info():
    """The brief is built only from observation fields the persona already
    legally sees - it must not invent opponents' hands or their battle card."""
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    obs = _obs_free(challengeable=True)
    note = brain._context_note(obs)
    # Own hand is fine to show; but there is no opponent-hand field in obs, so
    # the note must not contain any card list attributed to an opponent. Cheap
    # proxy: the only card names present belong to the "YOU:" hand line.
    hand_line = next(ln for ln in note.splitlines() if ln.startswith("YOU:"))
    for card in CARD_TYPES:
        # Cards may appear in the RPS rules sentence and the YOU line; assert
        # they never appear on a line mentioning another persona id.
        for ln in note.splitlines():
            if "0052" in ln or "0666" in ln:
                assert card not in ln, f"card {card} leaked on opponent line: {ln}"
    assert "Rock, Paper, Scissors, Rock" in hand_line


# ---------------------------------------------------------------------------
# 2. _run_vision_loop / decide: the brief reaches the model, clicks execute,
#    and the read-back action is returned.
# ---------------------------------------------------------------------------


def test_decide_threads_context_note_to_every_model_call(monkeypatch):
    primitives = [
        {"type": "click_at", "x": 550, "y": 700, "reasoning": "Arm duel."},
        {"type": "click_at", "x": 300, "y": 300, "reasoning": "Click Arlo."},
        {"type": "done", "reasoning": "Submitted."},
    ]
    last_action = {"action": "challenge", "target_id": "0052"}
    brain, page, seen = _make_brain(primitives, last_action, monkeypatch)

    result = brain.decide(_obs_free(challengeable=True))

    assert result["action"] == "challenge"
    assert result["target_id"] == "0052"
    # Same non-empty brief passed on every step this turn.
    assert seen and all("DUEL" in n for n in seen)
    assert len(set(seen)) == 1
    # Both click primitives actually dispatched to the (fake) browser.
    assert page.clicks == [(550.0, 700.0), (300.0, 300.0)]


def test_decide_executes_type_text_primitive(monkeypatch):
    primitives = [
        {"type": "type_text", "text": "Come closer", "reasoning": "Taunt."},
        {"type": "done"},
    ]
    last_action = {"action": "say", "text": "Come closer"}
    brain, page, _ = _make_brain(primitives, last_action, monkeypatch)
    result = brain.decide(_obs_free(challengeable=True))
    assert result["action"] == "say"
    assert page.typed == ["Come closer"]


def test_decide_attaches_last_reasoning(monkeypatch):
    primitives = [
        {"type": "click_at", "x": 1, "y": 1, "reasoning": "First thought."},
        {"type": "done", "reasoning": "Final rationale."},
    ]
    last_action = {"action": "move", "target_x": 5.0, "target_y": 5.0}
    brain, _, _ = _make_brain(primitives, last_action, monkeypatch)
    result = brain.decide(_obs_free(challengeable=True))
    # engine._extract_reasoning only logs non-empty reasoning; the latest
    # non-empty one from this turn should be attached.
    assert result.get("reasoning") == "Final rationale."


def test_decide_empty_menu_short_circuits_to_wait(monkeypatch):
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    brain._last_reasoning = None
    # No actions -> decide returns wait without ever touching the browser.
    result = brain.decide({"self": {}, "action_menu": {"actions": []}})
    assert result == {"action": "wait"}


# ---------------------------------------------------------------------------
# 3. Defensive sanitizer: an illegal / missing read-back falls back safely.
# ---------------------------------------------------------------------------


def test_decide_falls_back_when_readback_illegal(monkeypatch):
    # Model drives clicks but window.__lastAction reads back an illegal action
    # (challenge target not in the menu) -> sanitizer must fall back, not crash.
    primitives = [{"type": "done"}]
    last_action = {"action": "challenge", "target_id": "9999"}
    brain, _, _ = _make_brain(primitives, last_action, monkeypatch)
    result = brain.decide(_obs_free(challengeable=True))
    # Falls back to wait (first preference in _fallback) - a legal action.
    assert result["action"] in _obs_free(challengeable=True)["action_menu"]["actions"]
    assert result["action"] == "wait"


def test_decide_falls_back_when_loop_raises(monkeypatch):
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    brain._last_reasoning = None
    monkeypatch.setattr(vision_brain, "render_observation_html", lambda obs: "<html></html>")

    def boom():
        raise RuntimeError("browser exploded")

    brain._ensure_browser = boom  # blow up inside _run_vision_loop
    result = brain.decide(_obs_free(challengeable=True))
    # Any Playwright/SDK failure -> defensive fallback, still a legal action.
    assert result["action"] == "wait"


def test_sanitize_play_card_repairs_illegal_card():
    brain = BrowserVisionBrain.__new__(BrowserVisionBrain)
    obs = _obs_play_card()
    menu = obs["action_menu"]
    # Model somehow yields a card not in hand -> repaired to a legal one.
    out = brain._sanitize_decision({"action": "play_card", "card": "Paper"}, obs, menu)
    assert out["action"] == "play_card"
    assert out["card"] in menu["available_cards"]
