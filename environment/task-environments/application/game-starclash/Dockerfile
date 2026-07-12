FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# This task's actual Python deps: pyyaml (run_arena.py's YAML config
# loading), anthropic (ClaudeArenaBrain / BrowserVisionBrain - both
# import it lazily so a --brain mock/oracle run never needs it, but it's
# installed anyway so --brain claude/vision work for an agent without a
# rebuild), and gymnasium (gym_env.py's Gym-style wrapper around the
# engine, pinned to the exact version uv.lock resolved from the repo root
# pyproject.toml's "gymnasium>=1.0.0" constraint). playwright is pinned to
# match this base image's own tag exactly (v1.61.0-noble <->
# playwright==1.61.0); the image already bundles a matching Chromium plus
# all of its OS-level dependencies (fonts, libs, etc.), so no separate
# `playwright install` step is needed here - this mirrors the closest real
# precedent in this repo,
# environment/task-environments/application/example-web-playwright_books-interest/Dockerfile,
# which likewise never calls `playwright install` against this same base
# image family. (The CUA precedent's Xvfb/xfwm4/xfce4-terminal desktop stack
# is not used: BrowserVisionBrain drives Playwright's own headless Chromium
# directly, never a virtual X11 desktop, so that overhead is unnecessary
# here.)
RUN pip install --no-cache-dir pyyaml==6.0.3 anthropic==0.116.0 playwright==1.61.0 gymnasium==1.3.0

RUN mkdir -p /logs /app/input /app/scripts /app/persona/datasets/bench-dev-sample /app/output \
    && chmod 777 /logs /app/output

# Task-owned code and content, copied to the same /app/scripts + /app/input
# layout run_arena.py expects (see its --map/--crew/--out arguments and the
# solution/solve.sh oracle, which invokes it at exactly these paths).
COPY scripts/ /app/scripts/
COPY input/ /app/input/

# Full persona dataset referenced by crew_manifest*.yaml's persona_paths
# (e.g. "persona/datasets/bench-dev-sample/persona_0042.yaml"), placed as a
# sibling of scripts/ so run_arena.py's own repo-root walk-up (it walks up
# from its script directory looking for a "persona/datasets" directory)
# resolves those relative paths correctly inside the container.
COPY persona/ /app/persona/
