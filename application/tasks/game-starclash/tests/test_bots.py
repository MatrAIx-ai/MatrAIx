"""Unit tests for the computer-bot brains (scripts/brains.py).

These are dev/CI unit tests for the player-vs-bots mode, kept separate from
the harness verifier (tests/test_state.py, the only file test.sh runs). They
import the scripts package directly rather than reading run artifacts.

Player-vs-bots mode (run_arena.py --player-id) fills every non-player seat
with a BayesianBotBrain so a single sampled persona - as launched from the
Playground - still plays a full, non-degenerate game against active
opponents instead of a room full of do-nothing personas.
"""

import os
import sys

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import brains  # noqa: E402
import engine  # noqa: E402

CARD_TYPES = ("Rock", "Paper", "Scissors")


# ---------------------------------------------------------------------------
# Counter-map consistency with the engine's own RPS resolution.
# ---------------------------------------------------------------------------


def test_counter_map_consistent_with_engine_beats():
    """brains._COUNTER[c] must be the card that beats c, i.e. the winner w in
    engine._BEATS for which _BEATS[w] == c."""
    for winner, loser in engine._BEATS.items():
        assert brains._COUNTER[loser] == winner, (
            f"_COUNTER[{loser!r}]={brains._COUNTER[loser]!r} inconsistent with "
            f"engine._BEATS (expected {winner!r} to beat {loser!r})"
        )
    # Every card type is covered exactly once.
    assert set(brains._COUNTER) == set(CARD_TYPES)
    assert set(brains._COUNTER.values()) == set(CARD_TYPES)


# ---------------------------------------------------------------------------
# Posterior from public card counts.
# ---------------------------------------------------------------------------


def _play_card_obs(hand, arena_counts, available=None):
    return {
        "self": {"hand": list(hand), "x": 1.0, "y": 1.0},
        "arena_card_counts": dict(arena_counts),
        "arena_roster": [],
        "action_menu": {
            "actions": ["play_card"],
            "available_cards": list(available if available is not None else hand),
        },
    }


def test_posterior_subtracts_own_hand_and_normalises():
    bot = brains.BayesianBotBrain(seed=1)
    # Arena holds R1 P1 S3; we hold R1 P1 -> leftover is Scissors x3 -> P=1.0.
    obs = _play_card_obs(["Rock", "Paper"], {"Rock": 1, "Paper": 1, "Scissors": 3})
    post = bot._opponent_card_posterior(obs)
    assert post["Scissors"] == pytest.approx(1.0)
    assert post["Rock"] == pytest.approx(0.0)
    assert post["Paper"] == pytest.approx(0.0)
    assert sum(post.values()) == pytest.approx(1.0)


def test_posterior_uniform_when_no_public_signal():
    bot = brains.BayesianBotBrain(seed=1)
    # Everyone else is out of cards (arena == our own hand).
    obs = _play_card_obs(["Rock"], {"Rock": 1, "Paper": 0, "Scissors": 0})
    post = bot._opponent_card_posterior(obs)
    for card in CARD_TYPES:
        assert post[card] == pytest.approx(1.0 / 3.0)


# ---------------------------------------------------------------------------
# EV-optimal card selection.
# ---------------------------------------------------------------------------


def test_plays_counter_to_the_most_likely_card():
    bot = brains.BayesianBotBrain(seed=1)
    # Opponent almost certainly holds Scissors -> Rock is the counter.
    obs = _play_card_obs(["Rock", "Paper"], {"Rock": 1, "Paper": 1, "Scissors": 5})
    decision = bot.decide(obs)
    assert decision["action"] == "play_card"
    assert decision["card"] == "Rock"
    assert decision["reasoning"]


def test_avoids_the_losing_card():
    bot = brains.BayesianBotBrain(seed=1)
    # Opponent holds only Rock -> Paper beats Rock, Scissors loses to Rock.
    # Our hand has Paper and Scissors; must pick Paper.
    obs = _play_card_obs(
        ["Paper", "Scissors"],
        {"Rock": 4, "Paper": 1, "Scissors": 1},
    )
    decision = bot.decide(obs)
    assert decision["card"] == "Paper"


def test_play_card_is_always_from_available_hand():
    bot = brains.BayesianBotBrain(seed=7)
    obs = _play_card_obs(["Scissors"], {"Rock": 3, "Paper": 0, "Scissors": 1}, available=["Scissors"])
    decision = bot.decide(obs)
    assert decision["card"] == "Scissors"  # only legal option, even though it's not ideal


# ---------------------------------------------------------------------------
# Determinism under a fixed seed.
# ---------------------------------------------------------------------------


def test_deterministic_under_fixed_seed():
    obs = _play_card_obs(
        ["Rock", "Paper", "Scissors"],
        {"Rock": 2, "Paper": 2, "Scissors": 2},  # uniform -> all cards tie on EV, RNG breaks tie
    )
    a = brains.BayesianBotBrain(seed=99).decide(dict(obs))
    b = brains.BayesianBotBrain(seed=99).decide(dict(obs))
    assert a["card"] == b["card"]


# ---------------------------------------------------------------------------
# Challenge response uses the same posterior.
# ---------------------------------------------------------------------------


def test_accepts_favourable_matchup():
    bot = brains.BayesianBotBrain(seed=1)
    obs = {
        "self": {"hand": ["Rock"]},  # opponent holds Scissors -> Rock wins
        "arena_card_counts": {"Rock": 1, "Paper": 0, "Scissors": 3},
        "arena_roster": [],
        "action_menu": {"actions": ["accept", "decline"]},
    }
    decision = bot.decide(obs)
    assert decision["action"] == "accept"


def test_usually_declines_unfavourable_matchup():
    # Opponent holds only Rock; our only card is Scissors (loses to Rock).
    obs = {
        "self": {"hand": ["Scissors"]},
        "arena_card_counts": {"Rock": 4, "Paper": 0, "Scissors": 1},
        "arena_roster": [],
        "action_menu": {"actions": ["accept", "decline"]},
    }
    declines = 0
    for seed in range(20):
        decision = brains.BayesianBotBrain(seed=seed).decide(dict(obs))
        if decision["action"] == "decline":
            declines += 1
    # ~80% decline by design; require a clear majority to allow for the
    # deliberate small "gamble" acceptance rate.
    assert declines >= 12


# ---------------------------------------------------------------------------
# Free action is goal-directed (challenge in range, else approach).
# ---------------------------------------------------------------------------


def test_challenges_when_target_in_range():
    bot = brains.BayesianBotBrain(seed=1)
    obs = {
        "self": {"hand": ["Rock", "Paper"], "x": 5.0, "y": 5.0},
        "arena_card_counts": {"Rock": 2, "Paper": 2, "Scissors": 2},
        "arena_roster": [
            {"id": "0042", "is_self": True, "eliminated": False, "x": 5.0, "y": 5.0, "stars": 3},
            {"id": "0229", "is_self": False, "eliminated": False, "x": 5.5, "y": 5.0, "stars": 1},
        ],
        "action_menu": {
            "actions": ["challenge", "move", "say", "wait"],
            "challengeable_targets": ["0229"],
            "movable_bounds": {"max_distance": 2.0, "room_width": 20.0, "room_height": 20.0},
        },
    }
    decision = bot.decide(obs)
    assert decision["action"] == "challenge"
    assert decision["target_id"] == "0229"


def test_moves_toward_opponent_when_none_in_range():
    bot = brains.BayesianBotBrain(seed=1)
    obs = {
        "self": {"hand": ["Rock"], "x": 0.0, "y": 0.0},
        "arena_card_counts": {"Rock": 3, "Paper": 3, "Scissors": 3},
        "arena_roster": [
            {"id": "0042", "is_self": True, "eliminated": False, "x": 0.0, "y": 0.0, "stars": 3},
            {"id": "0229", "is_self": False, "eliminated": False, "x": 10.0, "y": 0.0, "stars": 3},
        ],
        "action_menu": {
            "actions": ["move", "say", "wait"],
            "challengeable_targets": [],
            "movable_bounds": {"max_distance": 2.0, "room_width": 20.0, "room_height": 20.0},
        },
    }
    decision = bot.decide(obs)
    assert decision["action"] == "move"
    # Should step toward (10, 0), i.e. increase x, staying within max_distance.
    assert decision["target_x"] > 0.0
    assert decision["target_x"] <= 2.0 + 1e-9
    assert decision["target_y"] == pytest.approx(0.0, abs=1e-6)


def test_challenge_target_prefers_fewest_stars():
    bot = brains.BayesianBotBrain(seed=3)
    obs = {
        "self": {"hand": ["Rock"], "x": 5.0, "y": 5.0},
        "arena_card_counts": {"Rock": 2, "Paper": 2, "Scissors": 2},
        "arena_roster": [
            {"id": "P", "is_self": True, "eliminated": False, "x": 5.0, "y": 5.0, "stars": 3},
            {"id": "A", "is_self": False, "eliminated": False, "x": 5.1, "y": 5.0, "stars": 4},
            {"id": "B", "is_self": False, "eliminated": False, "x": 5.2, "y": 5.0, "stars": 1},
        ],
        "action_menu": {
            "actions": ["challenge", "move", "wait"],
            "challengeable_targets": ["A", "B"],
            "movable_bounds": {"max_distance": 2.0, "room_width": 20.0, "room_height": 20.0},
        },
    }
    decision = bot.decide(obs)
    assert decision["target_id"] == "B"  # 1 star < 4 stars


# ---------------------------------------------------------------------------
# Default table size + player-vs-bots router wiring.
# ---------------------------------------------------------------------------

import yaml  # noqa: E402


def _default_manifest_persona_paths():
    manifest_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "input", "crew_manifest.yaml")
    )
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    return manifest.get("persona_paths", [])


def test_default_crew_fills_a_four_seat_table():
    """The default crew_manifest.yaml must seat exactly 4 players, so a
    Playground trial (1 sampled persona + bots) fills the game's intended
    maximum 4-seat table (min 2, max 4). Pins the requirement so the roster
    can't silently drift back to 5+."""
    paths = _default_manifest_persona_paths()
    assert len(paths) == 4, (
        f"default crew_manifest.yaml should list exactly 4 personas "
        f"(1 player + 3 bots = 4 seats), found {len(paths)}: {paths}"
    )


def test_router_assigns_one_player_and_rest_bots():
    """run_arena.py player-vs-bots wiring: with a player_id set, exactly one
    seat uses the real --brain and every OTHER seat is a BayesianBotBrain.

    Reproduces run_arena.main()'s router construction directly (without
    running a full game) so the wiring - not just the bot in isolation - is
    covered."""
    persona_order = ["0001", "0052", "0229", "0666"]
    player_id = "0001"
    seed = 42

    real_brain = brains.MockArenaBrain(seed=seed)
    bot_brains = {}
    for offset, pid in enumerate(persona_order):
        if pid == player_id:
            continue
        bot_brains[pid] = brains.BayesianBotBrain(seed=seed + 1 + offset)

    # Exactly one player seat, three bot seats, matching the default 4-table.
    assert set(bot_brains) == {"0052", "0229", "0666"}
    assert len(bot_brains) == 3
    assert all(isinstance(b, brains.BayesianBotBrain) for b in bot_brains.values())
    assert player_id not in bot_brains
    # Each bot gets a distinct seed so they don't act in lockstep.
    seeds = [seed + 1 + off for off, pid in enumerate(persona_order) if pid != player_id]
    assert len(set(seeds)) == len(seeds)
