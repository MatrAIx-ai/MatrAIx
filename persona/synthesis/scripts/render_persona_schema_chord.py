#!/usr/bin/env python3
"""Render a publication-quality two-ring chord diagram of the Persona schema.

The figure summarizes the Persona Full DAG at the taxonomy level, aligned to the
official taxonomy table (9 groups / 35 sub-categories / 1290 attributes):

- Inner ring: 35 sub-categories, each coloured by its parent group.
- Chord ribbons: directed-proposal edges aggregated to the sub-category level.
- Outer ring: the 9 top-level groups, spanning their sub-categories.

Notes on the aggregation:

- Latent/helper graph nodes (the 18 nodes with no ``category``, e.g. ``latent_*``
  / ``phase*_*``) are excluded, so the figure covers exactly the 1290 real
  persona attributes listed in the taxonomy table.
- The 8 ``Developer: *`` schema categories are merged into a single
  ``Developer/Coding`` sub-category, matching the taxonomy table.
- ``Demographic: Family`` (1 attribute, no modeled edges) is omitted because it
  would render as an empty stub with no ribbons.
- To keep the diagram readable, only sub-category pairs with at least
  ``--threshold`` aggregated edges (default 6) are drawn; weaker pairs are hidden.

Run from the repository root:

    uv run python persona/synthesis/scripts/render_persona_schema_chord.py

Writes ``persona_schema_chord.png`` and ``persona_schema_chord.pdf`` into
``persona/synthesis/visualization/``.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np
from pycirclize import Circos
import pycirclize.utils.plot as pcp

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH_PATH = REPO_ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
DEFAULT_OUT_DIR = REPO_ROOT / "persona" / "synthesis" / "visualization"

# OFFICIAL taxonomy: 9 groups -> sub-categories.
# Each entry is (group display name, group colour, [(sub-category display name,
# [schema category keys it aggregates]), ...]).
GROUPS = [
    ("Demographic\ninformation", "#4C72B0", [
        ("Basic", ["Demographic: Core"]),
        ("Life Events", ["Demographic: Life Events"]),
        ("Cultural", ["Demographic: Cultural"]),
    ]),
    ("Language and\ncommunication", "#8172B3", [
        ("Language", ["Linguistic: Language"]),
        ("Communication", ["Linguistic: Communication"]),
    ]),
    ("Education and professional\nbackground", "#B07AA1", [
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
    ("Values and\nworldview", "#C44E52", [
        ("Risk & Decision", ["Risk & Decision"]),
        ("Values & Motivation", ["Values & Motivation"]),
        ("Beliefs", ["Worldview: Beliefs"]),
    ]),
    ("Health and\naccessibility", "#59A14F", [
        ("Physical Health", ["Health: Physical"]),
        ("Fitness", ["Health: Fitness"]),
        ("Health Lifestyle", ["Health: Lifestyle"]),
    ]),
    ("Behavior and\ninteraction state", "#F1CE63", [
        ("Emotional State", ["State: Emotional"]),
        ("Time", ["Behavior: Time"]),
        ("Preferences", ["Behavior: Preferences"]),
        ("Work", ["Behavior: Work"]),
        ("Habits", ["Behavior: Habits"]),
    ]),
    ("Interests and\nculture", "#55A868", [
        ("Topics", ["Interests: Topics"]),
        ("Culture", ["Interests: Culture"]),
        ("Media", ["Interests: Media"]),
        ("Food", ["Interests: Food"]),
        ("Sports", ["Interests: Sports"]),
        ("Hobbies", ["Interests: Hobbies"]),
    ]),
]


def _patch_vertical_label_centering() -> None:
    """Centre vertical sector labels on their sector.

    pycirclize anchors vertical labels with ``va="center_baseline"`` and at the
    inner end of the word, which makes long labels look shifted off-centre and
    lets them grow radially into the outer group ring. Patch the label-parameter
    helper so vertical labels are centred both tangentially and radially.
    """
    original = pcp.get_label_params_by_rad

    def patched(rad, orientation, outer=True, only_rotation=False):
        params = original(rad, orientation, outer, only_rotation)
        if isinstance(params, dict):
            if params.get("va") == "center_baseline":
                params["va"] = "center"
            if orientation == "vertical" and "ha" in params:
                params["ha"] = "center"
        return params

    pcp.get_label_params_by_rad = patched


def _wrap_label(name: str, width: int = 9) -> str:
    """Break a long sub-category name onto a second line for a tidy radial label."""
    if len(name) <= width:
        return name
    if "/" in name:  # e.g. Developer/Coding, Industry/Role
        i = name.index("/")
        return name[:i + 1] + "\n" + name[i + 1:]
    if " " not in name:
        return name
    words = name.split(" ")
    best = None
    for k in range(1, len(words)):
        line1, line2 = " ".join(words[:k]), " ".join(words[k:])
        score = abs(len(line1) - len(line2))
        if best is None or score < best[0]:
            best = (score, line1 + "\n" + line2)
    return best[1]


def render(graph_path: Path, out_dir: Path, threshold: int = 6) -> None:
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["directed_proposal_edges"]
    node_category = {n["id"]: n.get("category") for n in nodes}

    # Ordered sub-category list and schema-category -> sub-category mapping.
    subgroups_ordered: list[str] = []
    sub_group: dict[str, str] = {}
    group_color: dict[str, str] = {}
    cat_to_sub: dict[str, str] = {}
    for group_name, group_col, subs in GROUPS:
        group_color[group_name] = group_col
        for disp, category_keys in subs:
            subgroups_ordered.append(disp)
            sub_group[disp] = group_name
            for key in category_keys:
                cat_to_sub[key] = disp
    index = {name: i for i, name in enumerate(subgroups_ordered)}
    n_sub = len(subgroups_ordered)

    def node_sub(node_id: str) -> str | None:
        category = node_category.get(node_id)
        return cat_to_sub.get(category) if category is not None else None

    covered = collections.Counter(
        node_sub(n["id"]) for n in nodes if node_sub(n["id"]) is not None
    )

    # Aggregate directed edges to the sub-category level and threshold.
    matrix = np.zeros((n_sub, n_sub))
    for edge in edges:
        src, dst = node_sub(edge["source"]), node_sub(edge["target"])
        if src in index and dst in index:
            matrix[index[src], index[dst]] += 1
    np.fill_diagonal(matrix, 0)
    matrix = np.where(matrix >= threshold, matrix, 0)

    # Give every sector a minimum arc so all labels fit without overlap.
    flow = matrix.sum(axis=1) + matrix.sum(axis=0)
    min_arc = max(230.0, flow.max() * 0.05)
    size = {
        subgroups_ordered[i]: float(max(flow[i], min_arc)) for i in range(n_sub)
    }

    _patch_vertical_label_centering()

    circos = Circos(size, space=3)
    for sector in circos.sectors:
        group_name = sub_group[sector.name]
        sector.axis(fc="none", ec="none")
        track = sector.add_track((90, 93))
        track.axis(fc=group_color[group_name], ec="white", lw=0.6)
        label = _wrap_label(sector.name)
        longest = max(len(line) for line in label.split("\n"))
        label_size = 15.5 if longest <= 11 else 13.5
        sector.text(label, r=107, size=label_size, adjust_rotation=True,
                    orientation="vertical", color="#222")

    # Draw chord ribbons, heaviest first, so thin links stay visible on top.
    cursor = {name: 0.0 for name in subgroups_ordered}
    order = sorted(
        ((i, j, matrix[i, j]) for i in range(n_sub) for j in range(n_sub)
         if matrix[i, j] > 0),
        key=lambda x: -x[2],
    )
    for i, j, weight in order:
        src, dst = subgroups_ordered[i], subgroups_ordered[j]
        u0, u1 = cursor[src], cursor[src] + weight
        cursor[src] = u1
        v0, v1 = cursor[dst], cursor[dst] + weight
        cursor[dst] = v1
        color = group_color[sub_group[src]]
        circos.link((src, u0, u1), (dst, v0, v1), color=color, alpha=0.5,
                    direction=1, r1=90, r2=90)

    # Outer 9-group ring (outside the sub-category labels) plus group labels.
    sector_by_name = {sector.name: sector for sector in circos.sectors}
    for group_name, group_col, subs in GROUPS:
        degrees: list[float] = []
        for disp, _ in subs:
            lo, hi = sector_by_name[disp].deg_lim
            degrees += [lo, hi]
        lo, hi = min(degrees), max(degrees)
        circos.rect(r_lim=(126, 132), deg_lim=(lo, hi), fc=group_col,
                    ec="white", lw=1.2)
        circos.text(group_name, r=147, deg=(lo + hi) / 2, size=20,
                    adjust_rotation=True, orientation="horizontal",
                    color=group_col, fontweight="bold", va="center", ha="center")

    fig = circos.plotfig(figsize=(18, 18))
    fig.suptitle("Persona schema", y=1.01, fontsize=19)

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / "persona_schema_chord.png"
    pdf_path = out_dir / "persona_schema_chord.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(
        f"wrote {png_path.relative_to(REPO_ROOT)} and "
        f"{pdf_path.relative_to(REPO_ROOT)} | sub-categories={n_sub} "
        f"attributes_covered={sum(covered.values())} (expect 1290)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--threshold", type=int, default=6,
        help="minimum aggregated edges for a sub-category pair to be drawn",
    )
    args = parser.parse_args()
    render(args.graph, args.out_dir, args.threshold)


if __name__ == "__main__":
    main()
