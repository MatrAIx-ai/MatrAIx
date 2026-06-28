# generate.py — Generate OASIS-compatible agent CSV and seed data from MatrAIx personas.
# Produces the exact CSV format OASIS expects for simulation experiments.
# Also generates initial seed posts and follow relationships.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from environment.oasis.persona_loader.adapter import (
    export_oasis_csv,
    load_personas_from_directory,
)
from environment.oasis.network.builder import (
    NetworkConfig,
    build_simple_topic_graph,
    build_social_graph,
)


def generate_twitter_dataset(
    persona_dir: str,
    output_dir: str,
    max_agents: int = 100,
    network_mode: str = "simple",
    follow_probability: float = 0.2,
    seed: int = 42,
):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    personas = load_personas_from_directory(persona_dir, max_agents=max_agents)
    print(f"Loaded {len(personas)} personas from {persona_dir}")

    if network_mode == "simple":
        graph = build_simple_topic_graph(personas, follow_probability=follow_probability, random_seed=seed)
    else:
        graph = build_social_graph(personas, NetworkConfig(random_seed=seed))

    print(f"Built graph: {graph.num_edges} edges, {len(graph.influencer_indices)} influencers")

    adj = graph.to_adjacency_list()
    following_lists = [adj[i] for i in range(len(personas))]

    csv_path = output_path / "agents.csv"
    export_oasis_csv(personas, csv_path, following_lists=following_lists, activity_frequency=100)
    print(f"Exported OASIS CSV: {csv_path}")

    seed_posts_path = output_path / "seed_posts.json"
    seed_posts = [{"user_id": sp.author_idx, "content": sp.content, "topic": sp.topic} for sp in graph.seed_posts]
    with open(seed_posts_path, "w") as f:
        json.dump(seed_posts, f, indent=2)
    print(f"Generated {len(seed_posts)} seed posts: {seed_posts_path}")

    edge_csv_path = output_path / "edges.csv"
    with open(edge_csv_path, "w") as f:
        f.write(graph.to_edge_list_csv())
    print(f"Exported edge list: {edge_csv_path}")

    meta = {
        "num_agents": len(personas),
        "num_edges": graph.num_edges,
        "num_influencers": len(graph.influencer_indices),
        "num_seed_posts": len(seed_posts),
        "network_mode": network_mode,
        "follow_probability": follow_probability,
        "seed": seed,
        "source_dir": persona_dir,
    }
    meta_path = output_path / "meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Metadata: {meta_path}")

    return csv_path


def main():
    parser = argparse.ArgumentParser(description="Generate OASIS-compatible simulation data from MatrAIx personas")
    parser.add_argument("--persona-dir", required=True, help="Path to persona YAML directory")
    parser.add_argument("--output-dir", default="environment/oasis/data/generated", help="Output directory")
    parser.add_argument("--max-agents", type=int, default=100, help="Max number of agents")
    parser.add_argument("--network-mode", choices=["simple", "affinity"], default="simple", help="Network generation mode")
    parser.add_argument("--follow-prob", type=float, default=0.2, help="Follow probability (simple mode)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    generate_twitter_dataset(
        persona_dir=args.persona_dir,
        output_dir=args.output_dir,
        max_agents=args.max_agents,
        network_mode=args.network_mode,
        follow_probability=args.follow_prob,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
