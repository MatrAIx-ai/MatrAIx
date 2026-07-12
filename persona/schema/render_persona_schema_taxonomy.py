#!/usr/bin/env python3
"""Render a clean taxonomy tree of the Persona schema for the paper appendix.

This is a three-level horizontal bracket tree:

- **Group** (9 top-level groups, aligned to the official taxonomy table).
- **Aspect** (the schema-prefix mid level, e.g. ``Demographic``, ``Linguistic``,
  ``Developer``).
- **Category** (the fine-grained leaf categories, with attribute counts).

The grouping is aligned to the official taxonomy table (9 groups, 1290
attributes). Unlike the chord diagram, this figure is not derived from the DAG
edges; it is a conceptual taxonomy that reflects the schema structure. It shows
all fine-grained categories (43 leaves), including the individual ``Developer``
categories, so it is a more detailed companion to the compact table.

Run from the repository root:

    uv run --extra viz python persona/schema/render_persona_schema_taxonomy.py

Writes ``persona_schema_taxonomy.png`` and ``persona_schema_taxonomy.pdf`` into
``persona/schema/``.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.path import Path as MplPath

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_PATH = REPO_ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
DEFAULT_OUT_DIR = REPO_ROOT / "persona" / "schema"

# OFFICIAL taxonomy: 9 groups -> aspects -> categories, in table order.
# Each group is (group display name, group colour, [aspect, ...]);
# each aspect is (aspect display name, [(category display name, schema key), ...]).
GROUPS = [
    ("Demographic information", "#4C72B0", [
        ("Demographic", [
            ("Basic", "Demographic: Core"),
            ("Life Events", "Demographic: Life Events"),
            ("Cultural", "Demographic: Cultural"),
            ("Family", "Demographic: Family"),
        ]),
    ]),
    ("Language and communication", "#8172B3", [
        ("Linguistic", [
            ("Language", "Linguistic: Language"),
            ("Communication", "Linguistic: Communication"),
        ]),
    ]),
    ("Education and professional background", "#B07AA1", [
        ("Learning", [
            ("Academic", "Learning: Academic"),
            ("Learning Style", "Learning: Style"),
        ]),
        ("Professional", [
            ("Career", "Professional: Career"),
            ("Industry/Role", "Professional: Industry"),
        ]),
    ]),
    ("Expertise and skills", "#DD8452", [
        ("Expertise", [
            ("Domains", "Expertise: Domains"),
            ("Skills", "Expertise: Skills"),
        ]),
        ("Skills", [
            ("Tools", "Skills: Tools"),
            ("Programming", "Skills: Programming"),
        ]),
        ("Developer", [
            ("AI Workflow Tasks", "Developer: AI Workflow Tasks"),
            ("Agent Adoption", "Developer: Agent Adoption"),
            ("Code Maintenance", "Developer: Code Maintenance"),
            ("AI Adoption", "Developer: AI Adoption"),
            ("Technology Evaluation", "Developer: Technology Evaluation"),
            ("Open Source Behavior", "Developer: Open Source Behavior"),
            ("Professional Context", "Developer: Professional Context"),
            ("Community Behavior", "Developer: Community Behavior"),
        ]),
    ]),
    ("Personality", "#CCB974", [
        ("Personality", [
            ("Character", "Personality: Character"),
            ("Big Five", "Personality: Big Five"),
            ("MBTI", "Personality: MBTI"),
            ("Relationships", "Personality: Relationships"),
        ]),
    ]),
    ("Values and worldview", "#C44E52", [
        ("Risk & Decision", [
            ("Risk & Decision", "Risk & Decision"),
        ]),
        ("Values & Motivation", [
            ("Values & Motivation", "Values & Motivation"),
        ]),
        ("Worldview", [
            ("Beliefs", "Worldview: Beliefs"),
        ]),
    ]),
    ("Health and accessibility", "#17A2B8", [
        ("Health", [
            ("Physical Health", "Health: Physical"),
            ("Fitness", "Health: Fitness"),
            ("Health Lifestyle", "Health: Lifestyle"),
        ]),
    ]),
    ("Behavior and interaction state", "#F1CE63", [
        ("State", [
            ("Emotional State", "State: Emotional"),
        ]),
        ("Behavior", [
            ("Time", "Behavior: Time"),
            ("Preferences", "Behavior: Preferences"),
            ("Work", "Behavior: Work"),
            ("Habits", "Behavior: Habits"),
        ]),
    ]),
    ("Interests and culture", "#55A868", [
        ("Interests", [
            ("Topics", "Interests: Topics"),
            ("Culture", "Interests: Culture"),
            ("Media", "Interests: Media"),
            ("Food", "Interests: Food"),
            ("Sports", "Interests: Sports"),
            ("Hobbies", "Interests: Hobbies"),
        ]),
    ]),
]

TEXT_COLOR = "#111111"


def _display_path(path: Path) -> str:
    """Show a repo-relative path when possible, else the absolute path."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _lighten(hex_color: str, factor: float) -> tuple[float, float, float]:
    r, g, b = mcolors.to_rgb(hex_color)
    return (r + (1 - r) * factor, g + (1 - g) * factor, b + (1 - b) * factor)


def _wrap(text: str, width: int) -> str:
    """Greedy word wrap so long names fit inside a box on multiple lines."""
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines)


def render(graph_path: Path, out_dir: Path) -> None:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    counts = collections.Counter(n.get("category") for n in graph["nodes"])

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    # Vertical layout: leaves top-to-bottom, uniform spacing within a group and
    # a small gap between groups.
    step = 1.0
    group_gap = 0.8
    y_leaf: list[float] = []
    leaf_meta: list[tuple[str, int, str]] = []            # (display, count, colour)
    aspect_spans: list[tuple[str, str, list[int]]] = []   # (aspect, colour, leaf idxs)
    group_spans: list[tuple[str, str, int, list[int]]] = []  # (group, colour, total, aspect idxs)

    cursor = 0.0
    leaf_i = 0
    for group_name, color, aspects in GROUPS:
        group_total = 0
        aspect_idxs: list[int] = []
        for aspect_name, cats in aspects:
            idxs: list[int] = []
            for disp, key in cats:
                count = counts[key]
                group_total += count
                y_leaf.append(cursor)
                leaf_meta.append((disp, count, color))
                idxs.append(leaf_i)
                leaf_i += 1
                cursor -= step
            aspect_idxs.append(len(aspect_spans))
            aspect_spans.append((aspect_name, color, idxs))
        group_spans.append((group_name, color, group_total, aspect_idxs))
        cursor -= group_gap

    shift = min(y_leaf)
    y_leaf = [y - shift for y in y_leaf]
    span = max(y_leaf)

    fig, ax = plt.subplots(figsize=(13.5, 0.30 * (span + 2) + 1.0))
    ax.axis("off")

    x_group, w_group = 0.0, 3.9
    x_aspect, w_aspect = 4.9, 3.9
    x_leaf, w_leaf = 9.4, 4.2
    leaf_h = 0.66

    def draw_box(x, y, w, h, text, face, edge, size):
        ax.add_patch(FancyBboxPatch(
            (x, y - h / 2), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.0, edgecolor=edge, facecolor=face, zorder=3))
        ax.text(x + w / 2, y, text, ha="center", va="center", fontsize=size,
                color=TEXT_COLOR, zorder=4)

    def connect(x0, y0, x1, y1, color):
        xm = (x0 + x1) / 2
        ax.add_patch(mpatches.PathPatch(MplPath(
            [(x0, y0), (xm, y0), (xm, y1), (x1, y1)],
            [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]),
            fill=False, edgecolor=color, lw=1.0, alpha=0.55, zorder=1))

    # Category boxes (leaves).
    for i, (disp, count, color) in enumerate(leaf_meta):
        draw_box(x_leaf, y_leaf[i], w_leaf, leaf_h, f"{disp}  ({count})",
                 _lighten(color, 0.80), color, size=11.0)

    # Aspect boxes (mid) at the mean y of their leaves, with brackets to leaves.
    aspect_y: list[float] = []
    for aspect_name, color, idxs in aspect_spans:
        y_mid = float(np.mean([y_leaf[i] for i in idxs]))
        aspect_y.append(y_mid)
        label = _wrap(aspect_name, 20)
        n_lines = label.count("\n") + 1
        draw_box(x_aspect, y_mid, w_aspect, n_lines * 0.46 + 0.28, label,
                 _lighten(color, 0.58), color, size=11.5)
        for i in idxs:
            connect(x_aspect + w_aspect, y_mid, x_leaf, y_leaf[i], color)

    # Group boxes at the mean y of their aspects, with brackets to aspects.
    for group_name, color, total, aspect_idxs in group_spans:
        y_mid = float(np.mean([aspect_y[a] for a in aspect_idxs]))
        label = f"{_wrap(group_name, 24)}\n({total})"
        n_lines = label.count("\n") + 1
        draw_box(x_group, y_mid, w_group, n_lines * 0.50 + 0.28, label,
                 _lighten(color, 0.40), color, size=12.0)
        for a in aspect_idxs:
            connect(x_group + w_group, y_mid, x_aspect, aspect_y[a], color)

    # Column headers.
    top = span + 1.3
    ax.text(x_group + w_group / 2, top, "Group  (# attributes)",
            ha="center", va="center", fontsize=12.5, color=TEXT_COLOR)
    ax.text(x_aspect + w_aspect / 2, top, "Aspect",
            ha="center", va="center", fontsize=12.5, color=TEXT_COLOR)
    ax.text(x_leaf + w_leaf / 2, top, "Category  (# attributes)",
            ha="center", va="center", fontsize=12.5, color=TEXT_COLOR)

    ax.set_xlim(-0.4, x_leaf + w_leaf + 0.4)
    ax.set_ylim(-1.0, top + 1.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "persona_schema_taxonomy.png"
    pdf_path = out_dir / "persona_schema_taxonomy.pdf"
    fig.savefig(png_path, dpi=300, facecolor="white")
    fig.savefig(pdf_path, facecolor="white")
    plt.close(fig)
    grand_total = sum(total for _n, _c, total, _a in group_spans)
    print(
        f"wrote {_display_path(png_path)} and {_display_path(pdf_path)} | "
        f"groups={len(GROUPS)} aspects={len(aspect_spans)} "
        f"categories={len(leaf_meta)} attributes={grand_total} (expect 1290)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    render(args.graph, args.out_dir)


if __name__ == "__main__":
    main()
