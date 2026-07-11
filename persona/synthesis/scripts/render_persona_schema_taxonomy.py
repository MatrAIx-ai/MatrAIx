#!/usr/bin/env python3
"""Render a clean taxonomy tree of the Persona schema for the paper appendix.

This is a horizontal bracket tree that mirrors the official taxonomy table
(9 groups / 36 sub-categories / 1290 attributes):

- Left column: the 9 top-level groups (with attribute totals).
- Right column: the 36 sub-categories (with attribute counts).
- Brackets connect each group to its sub-categories.

Unlike the chord diagram, this figure is not derived from the DAG edges; it is a
conceptual taxonomy that reflects the schema structure exactly as listed in the
table. All 36 sub-categories are shown (including small ones such as ``Family``),
and the 8 ``Developer: *`` schema categories are merged into a single
``Developer/Coding`` sub-category to match the table.

Run from the repository root:

    uv run --extra viz python persona/synthesis/scripts/render_persona_schema_taxonomy.py

Writes ``persona_schema_taxonomy.png`` and ``persona_schema_taxonomy.pdf`` into
``persona/synthesis/visualization/``.
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

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH_PATH = REPO_ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
DEFAULT_OUT_DIR = REPO_ROOT / "persona" / "synthesis" / "visualization"

# OFFICIAL taxonomy: 9 groups -> sub-categories, in table order.
# Each entry is (group display name, group colour, [(sub-category display name,
# [schema category keys it aggregates]), ...]).
GROUPS = [
    ("Demographic information", "#4C72B0", [
        ("Basic", ["Demographic: Core"]),
        ("Life Events", ["Demographic: Life Events"]),
        ("Cultural", ["Demographic: Cultural"]),
        ("Family", ["Demographic: Family"]),
    ]),
    ("Language and communication", "#8172B3", [
        ("Language", ["Linguistic: Language"]),
        ("Communication", ["Linguistic: Communication"]),
    ]),
    ("Education and professional background", "#B07AA1", [
        ("Academic", ["Learning: Academic"]),
        ("Learning Style", ["Learning: Style"]),
        ("Career", ["Professional: Career"]),
        ("Industry/Role", ["Professional: Industry"]),
    ]),
    ("Expertise and skills", "#DD8452", [
        ("Domains", ["Expertise: Domains"]),
        ("Skills", ["Expertise: Skills"]),
        ("Tools", ["Skills: Tools"]),
        ("Programming", ["Skills: Programming"]),
        ("Developer/Coding", [
            "Developer: AI Workflow Tasks", "Developer: Agent Adoption",
            "Developer: Code Maintenance", "Developer: AI Adoption",
            "Developer: Technology Evaluation", "Developer: Open Source Behavior",
            "Developer: Professional Context", "Developer: Community Behavior",
        ]),
    ]),
    ("Personality", "#CCB974", [
        ("Character", ["Personality: Character"]),
        ("Big Five", ["Personality: Big Five"]),
        ("MBTI", ["Personality: MBTI"]),
        ("Relationships", ["Personality: Relationships"]),
    ]),
    ("Values and worldview", "#C44E52", [
        ("Risk & Decision", ["Risk & Decision"]),
        ("Values & Motivation", ["Values & Motivation"]),
        ("Beliefs", ["Worldview: Beliefs"]),
    ]),
    ("Health and accessibility", "#59A14F", [
        ("Physical Health", ["Health: Physical"]),
        ("Fitness", ["Health: Fitness"]),
        ("Health Lifestyle", ["Health: Lifestyle"]),
    ]),
    ("Behavior and interaction state", "#F1CE63", [
        ("Emotional State", ["State: Emotional"]),
        ("Time", ["Behavior: Time"]),
        ("Preferences", ["Behavior: Preferences"]),
        ("Work", ["Behavior: Work"]),
        ("Habits", ["Behavior: Habits"]),
    ]),
    ("Interests and culture", "#55A868", [
        ("Topics", ["Interests: Topics"]),
        ("Culture", ["Interests: Culture"]),
        ("Media", ["Interests: Media"]),
        ("Food", ["Interests: Food"]),
        ("Sports", ["Interests: Sports"]),
        ("Hobbies", ["Interests: Hobbies"]),
    ]),
]

TEXT_COLOR = "#111111"


def _lighten(hex_color: str, factor: float) -> tuple[float, float, float]:
    r, g, b = mcolors.to_rgb(hex_color)
    return (r + (1 - r) * factor, g + (1 - g) * factor, b + (1 - b) * factor)


def _wrap(text: str, width: int) -> str:
    """Greedy word wrap so long group names fit inside a box on two/three lines."""
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

    # Flatten to leaves and compute counts.
    leaves: list[tuple[str, str, str, int]] = []  # (group, colour, subgroup, count)
    group_total: dict[str, int] = {}
    for group_name, color, subs in GROUPS:
        total = 0
        for disp, keys in subs:
            count = sum(counts[key] for key in keys)
            total += count
            leaves.append((group_name, color, disp, count))
        group_total[group_name] = total

    n_leaf = len(leaves)
    grand_total = sum(group_total.values())

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    # Vertical layout: leaves top-to-bottom, uniform spacing.
    step = 1.0
    y_leaf = {i: (n_leaf - i) * step for i in range(n_leaf)}

    fig, ax = plt.subplots(figsize=(11, 0.42 * n_leaf + 1.4))
    ax.axis("off")

    x_group, w_group = 0.0, 3.4
    x_sub, w_sub = 5.2, 4.2
    box_h = 0.78

    def draw_box(x, y, w, text, face, edge, size):
        ax.add_patch(FancyBboxPatch(
            (x, y - box_h / 2), w, box_h,
            boxstyle="round,pad=0.02,rounding_size=0.14",
            linewidth=1.0, edgecolor=edge, facecolor=face, zorder=3))
        ax.text(x + w / 2, y, text, ha="center", va="center", fontsize=size,
                color=TEXT_COLOR, zorder=4)

    def connect(x0, y0, x1, y1, color):
        xm = (x0 + x1) / 2
        ax.add_patch(mpatches.PathPatch(MplPath(
            [(x0, y0), (xm, y0), (xm, y1), (x1, y1)],
            [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4]),
            fill=False, edgecolor=color, lw=1.0, alpha=0.6, zorder=1))

    # Sub-category boxes (leaves).
    for i, (_group, color, disp, count) in enumerate(leaves):
        draw_box(x_sub, y_leaf[i], w_sub, f"{disp}  ({count})",
                 _lighten(color, 0.80), color, size=9.5)

    # Group boxes at the mean y of their sub-categories, with brackets.
    leaf_index = 0
    for group_name, color, subs in GROUPS:
        idxs = list(range(leaf_index, leaf_index + len(subs)))
        leaf_index += len(subs)
        y_mid = float(np.mean([y_leaf[i] for i in idxs]))
        label = f"{_wrap(group_name, 22)}\n({group_total[group_name]})"
        draw_box(x_group, y_mid, w_group, label,
                 _lighten(color, 0.42), color, size=10.5)
        for i in idxs:
            connect(x_group + w_group, y_mid, x_sub, y_leaf[i], color)

    # Column headers.
    top = n_leaf * step + 1.1
    ax.text(x_group + w_group / 2, top, "Group  (# attributes)",
            ha="center", va="center", fontsize=10.5, color=TEXT_COLOR)
    ax.text(x_sub + w_sub / 2, top, "Sub-category  (# attributes)",
            ha="center", va="center", fontsize=10.5, color=TEXT_COLOR)

    ax.set_xlim(-0.4, x_sub + w_sub + 0.4)
    ax.set_ylim(0.0, top + 1.2)
    ax.set_title(
        f"Taxonomy of the MatrAIx persona schema ({grand_total:,} attributes)",
        fontsize=13, color=TEXT_COLOR, pad=10)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "persona_schema_taxonomy.png"
    pdf_path = out_dir / "persona_schema_taxonomy.pdf"
    fig.savefig(png_path, dpi=300, facecolor="white")
    fig.savefig(pdf_path, facecolor="white")
    plt.close(fig)
    print(
        f"wrote {png_path.relative_to(REPO_ROOT)} and "
        f"{pdf_path.relative_to(REPO_ROOT)} | groups={len(GROUPS)} "
        f"sub-categories={n_leaf} attributes={grand_total} (expect 1290)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    render(args.graph, args.out_dir)


if __name__ == "__main__":
    main()
