#!/usr/bin/env bash
set -euo pipefail

mkdir -p /app/output

python3 /app/scripts/stage_crew_personas.py --crew /app/input/crew_manifest.yaml

# Oracle for the Starclash task: run the deterministic,
# no-API-key MockArenaBrain against the task's own ship map + crew roster
# and write game_log.json / final_state.json to /app/output. Seed 42 with
# --max-ticks 20 is a known-good combination (multiple battles resolved
# before the tick budget runs out, confirmed by re-running run_arena.py
# directly), so this oracle run is fully deterministic and reproducibly
# produces at least one battle_resolved event. The game also ends early on
# its own if every active persona empties their hand (termination_reason
# "all_cards_played") or only one survivor remains ("one_survivor").
# Player-vs-bots: run_arena.py reads STARCLASH_PLAYER_ID / STARCLASH_OPPONENT_BRAIN
# from the environment (set via task.toml [solution.env]; the launch service
# fills MATRIX_STARCLASH_PLAYER_ID with the sampled persona, else "auto" =
# first crew persona). The other seats are Bayesian bots. --player-id auto is
# passed explicitly so this is a full player-vs-bots game even when the env var
# is unset.
#
# Player brain: defaults to "mock" (the deterministic, no-API-key oracle). Set
# STARCLASH_PLAYER_BRAIN=vision (with AWS_BEARER_TOKEN_BEDROCK + AWS_REGION, or
# ANTHROPIC_API_KEY) to have the sampled persona play live via BrowserVisionBrain
# — a real screenshot->click computer-use loop over the rendered HUD — so the
# batch report reflects a genuine live run instead of the deterministic replay.
python3 /app/scripts/run_arena.py \
  --map /app/input/ship_map.yaml \
  --crew /app/input/crew_manifest.yaml \
  --brain "${STARCLASH_PLAYER_BRAIN:-mock}" \
  --player-id "${STARCLASH_PLAYER_ID:-auto}" \
  --opponent-brain "${STARCLASH_OPPONENT_BRAIN:-bayesian}" \
  --seed 42 \
  --max-ticks 50 \
  --render-spectator \
  --out /app/output
