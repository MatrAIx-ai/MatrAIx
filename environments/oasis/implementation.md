# OASIS Implementation Plan

> How we integrate OASIS into MatrAIx: load personas, build social graphs, run simulations, extract traces.

---

## Module Overview

```
environments/oasis/
├── README.md                  # Reference documentation (done)
├── implementation.md          # This file
├── persona_adapter.py         # Module 1: MatrAIx personas → OASIS agents
├── network_builder.py         # Module 2: Social graph construction
├── simulation_runner.py       # Module 3: Configure + run OASIS simulation
├── trace_analyzer.py          # Module 4: Extract + analyze outputs
├── config.yaml                # Default simulation configuration
└── tests/
    ├── test_persona_adapter.py
    ├── test_network_builder.py
    ├── test_simulation_runner.py
    └── test_trace_analyzer.py
```

---

## Module 1: Persona Adapter (`persona_adapter.py`)

**Purpose**: Convert MatrAIx persona YAML files into OASIS-compatible `UserInfo` objects.

### Input

MatrAIx persona YAML (from `personas/Jun20_1k_persona_description/`):

```yaml
metadata:
  id: ID0001
persona:
  name: Nikhil Desai
  title: Mid in Social Services & NGO
  age: 59
  description: "59-year-old man based in South Asia..."
  dimensions:
    region: South Asia
    gender_identity: Man
    age_bracket: 55–64
    urbanicity: Suburban
    socioeconomic_band: Lower-middle
    domain: Social Services & NGO
    primary_language: Hindi
    english_proficiency: Intermediate (B1–B2)
    marital_status: Single
    children: No children
    emotional_state: Concerned
    intent: help others
    personality_big5_openness: Medium
    personality_big5_conscientiousness: Very high
    personality_big5_extraversion: High
    personality_big5_agreeableness: Low
    personality_big5_neuroticism: Medium
```

### Output

OASIS `UserInfo` object:

```python
UserInfo(
    name="Nikhil Desai",
    user_name="nikhil_desai_0001",
    description="Mid in Social Services & NGO. 59-year-old man based in South Asia...",
    profile={
        "other_info": {
            "user_profile": "<rich persona text from description + dimensions>",
            "mbti": "ENFJ",  # derived from Big Five mapping
            "gender": "male",
            "age": 59,
            "country": "India",
            "profession": "Social Services & NGO",
            "interested_topics": ["Social Work", "Community Development"],
            "active_threshold": [0.01] * 24,  # hourly activity probability
        }
    }
)
```

### Implementation Steps

1. **Load YAML batch** — Read all persona files from a directory (or accept a list of paths).
2. **Map dimensions → OASIS fields**:
   - `gender_identity` → `gender`
   - `region` → `country` (map "South Asia" → random country in region, or keep region)
   - `domain` → `profession`
   - `personality_big5_*` → derive approximate MBTI (OpenNess+Extraversion→I/E, etc.)
   - `intent` + `domain` → `interested_topics` (map to OASIS's 9 topic categories)
3. **Generate username** — Slugify name + append persona ID.
4. **Build user_profile text** — Combine `description` + key dimensions into a natural-language persona paragraph that the LLM will see as its system prompt.
5. **Set activity probability** — Based on `age_bracket` and `urbanicity` (younger/urban → higher activity).
6. **Return list of UserInfo** — Ready to feed into Module 2.

### Key Decisions

- Big Five → MBTI mapping is lossy but OASIS expects MBTI. We use the standard approximate mapping (high O + high E → ENFP, etc.). Alternatively, we can patch OASIS to accept Big Five directly in the system prompt.
- For `interested_topics`, we define a mapping from MatrAIx `domain` values to OASIS topic categories (Technology, Business, Health, etc.).
- Activity thresholds can be uniform (simple) or vary by persona traits (high extraversion → higher threshold).

---

## Module 2: Network Builder (`network_builder.py`)

**Purpose**: Construct the initial social graph (who follows whom) from persona attributes.

### Strategy

OASIS requires a directed follow graph. We build it from persona similarity:

1. **Topic-based clustering** — Group personas by `domain` / `interested_topics`. Users within the same topic cluster have a higher probability of following each other.
2. **Influencer seeding** — Select N "seed" accounts per topic (high extraversion, high conscientiousness) that many others follow, creating a scale-free topology.
3. **Cross-topic bridges** — Small probability of following users from different topics (prevents isolated clusters).

### Implementation Steps

1. **Accept list of personas** (output of Module 1).
2. **Cluster by topic** — Group personas into topic buckets.
3. **Generate follow edges**:
   - Within-topic: each user follows 5–20 others in same topic (probability weighted by similarity).
   - Influencers: top 5% by extraversion score get 10x more followers.
   - Cross-topic: 10% probability of following 1–3 users from a different topic.
4. **Output**: Either an igraph `Graph(directed=True)` for <100K agents, or a CSV of `(follower_id, followee_id)` pairs for larger scale.
5. **Optionally generate seed posts** — Create 1–3 initial posts per influencer to bootstrap the feed.

### Configuration

```yaml
network:
  within_topic_follow_range: [5, 20]
  influencer_percentile: 0.95
  influencer_follower_multiplier: 10
  cross_topic_probability: 0.10
  cross_topic_follow_range: [1, 3]
  seed_posts_per_influencer: 3
```

---

## Module 3: Simulation Runner (`simulation_runner.py`)

**Purpose**: Configure and execute the OASIS simulation end-to-end.

### Responsibilities

1. **Initialize LLM backend** — Connect to vLLM endpoints (Greenland) or OpenAI API (dev/testing).
2. **Build AgentGraph** — Create `SocialAgent` instances from Module 1 output, wire up the Module 2 graph.
3. **Configure Platform** — Set recsys type, action space, clock settings.
4. **Run simulation loop** — Execute N timesteps with configurable activation probability.
5. **Checkpoint** — Periodically save the SQLite database for resumability.
6. **Shutdown** — Clean close of environment.

### Implementation Steps

1. **Load config** (`config.yaml`):

```yaml
simulation:
  num_timesteps: 50
  semaphore: 128
  platform_type: twitter          # twitter | reddit
  recsys_type: twitter            # random | reddit | twitter | twhin-bert
  activation_probability: 0.05   # fraction of agents acting per step
  checkpoint_every: 10           # save DB every N steps

inference:
  backend: vllm                   # vllm | openai | anthropic
  model: meta-llama/Meta-Llama-3-8B-Instruct
  endpoints:
    - host: localhost
      ports: [8002, 8003, 8004, 8005]

actions:
  available:
    - do_nothing
    - create_post
    - repost
    - like_post
    - dislike_post
    - create_comment
    - follow
    - unfollow

persona:
  source_dir: ../../personas/Jun20_1k_persona_description/
  max_agents: 1000               # limit for testing

network:
  within_topic_follow_range: [5, 20]
  influencer_percentile: 0.95
  cross_topic_probability: 0.10
  seed_posts_per_influencer: 3

output:
  database_path: ./data/simulation.db
  checkpoint_dir: ./data/checkpoints/
```

2. **Main entry point**:

```python
async def run_simulation(config_path: str):
    config = load_config(config_path)

    # Module 1: Load and convert personas
    personas = load_personas(config["persona"]["source_dir"], max_agents=config["persona"]["max_agents"])
    user_infos = adapt_personas(personas)

    # Module 2: Build social network
    graph, seed_posts = build_network(user_infos, config["network"])

    # Module 3: Initialize OASIS
    agents = create_agents(user_infos, graph, config["inference"])
    env = oasis.make(
        agent_graph=agents,
        platform=config["simulation"]["platform_type"],
        database_path=config["output"]["database_path"],
        semaphore=config["simulation"]["semaphore"],
    )

    await env.reset()
    inject_seed_posts(env, seed_posts)

    # Simulation loop
    for t in range(config["simulation"]["num_timesteps"]):
        active_agents = select_active_agents(agents, config["simulation"]["activation_probability"])
        actions = {agent: LLMAction() for agent in active_agents}
        await env.step(actions)

        if (t + 1) % config["simulation"]["checkpoint_every"] == 0:
            checkpoint(env, config["output"]["checkpoint_dir"], t)

    await env.close()

    # Module 4: Analyze
    results = analyze_traces(config["output"]["database_path"])
    return results
```

3. **LLM backend setup**:
   - For Greenland: start vLLM servers on the 8 A100s, connect via localhost ports.
   - For dev/testing: use OpenAI API with `gpt-4o-mini` (cheap, fast).
   - CAMEL's `ModelFactory` handles both via `ModelPlatformType.VLLM` or `ModelPlatformType.OPENAI`.

### Running

```bash
# Dev (OpenAI API, 10 agents)
python -m environments.oasis.simulation_runner --config environments/oasis/config.yaml

# Greenland (vLLM, 1000 agents)
./scripts/greenland-sync.sh push
./scripts/greenland-sync.sh runbg "python -m environments.oasis.simulation_runner --config environments/oasis/config.yaml"
```

---

## Module 4: Trace Analyzer (`trace_analyzer.py`)

**Purpose**: Extract simulation traces from SQLite and produce analysis reports.

### What We Extract

From the `trace` table (every agent action with full JSON):
- **Information spread**: How many reposts/quotes did each seed post generate? What's the cascade depth?
- **Engagement metrics**: Likes, comments, reposts per post; engagement rate by persona type.
- **Network evolution**: New follows/unfollows over time; cluster formation.
- **Behavioral patterns**: Do personas with high neuroticism post differently? Do introverts engage less?
- **Polarization**: Do agents cluster into echo chambers? Do cross-topic bridges prevent it?

### Implementation Steps

1. **Connect to SQLite database** (output of Module 3).
2. **Extract raw traces** — Query `trace`, `post`, `follow`, `like`, `comment` tables.
3. **Compute metrics**:
   - Per-agent: posts created, likes given/received, follows gained/lost, activity rate
   - Per-post: reach (unique views), engagement rate, cascade depth
   - Network-level: clustering coefficient, average path length, community detection
   - Temporal: activity curves, information velocity, opinion drift
4. **Persona-conditioned analysis** — Group metrics by persona dimensions (age, region, Big Five, domain) to answer: "Do personas with trait X behave differently from trait Y?"
5. **Generate report** — JSON + optional markdown summary.

### Output Format

```json
{
    "simulation_meta": {
        "num_agents": 1000,
        "num_timesteps": 50,
        "platform": "twitter",
        "recsys": "twitter",
        "total_actions": 12450
    },
    "aggregate_metrics": {
        "total_posts": 890,
        "total_reposts": 340,
        "total_likes": 2100,
        "total_comments": 560,
        "total_follows": 1200,
        "avg_engagement_rate": 0.034
    },
    "persona_breakdown": {
        "by_age_bracket": { "18-24": {...}, "25-34": {...}, ... },
        "by_big5_extraversion": { "High": {...}, "Medium": {...}, "Low": {...} },
        "by_domain": { "Technology": {...}, "Healthcare": {...}, ... }
    },
    "network_evolution": {
        "initial_edges": 8500,
        "final_edges": 9700,
        "new_follows": 1200,
        "unfollows": 0,
        "communities_detected": 7
    },
    "information_spread": {
        "avg_cascade_depth": 2.3,
        "max_cascade_depth": 8,
        "viral_posts": [{"post_id": 42, "reach": 340, "reposts": 28}]
    }
}
```

---

## Implementation Order

| Phase | Module | Effort | Depends On |
|-------|--------|--------|------------|
| **Phase 1** | Module 1 (Persona Adapter) | 1–2 days | MatrAIx persona YAMLs |
| **Phase 2** | Module 2 (Network Builder) + Module 3 (Simulation Runner) | 2–3 days | Module 1 |
| **Phase 3** | Module 4 (Trace Analyzer) | 1–2 days | Module 3 output |

### Phase 1: Get personas into OASIS format

- Start with the 1,000 personas already generated (`personas/Jun20_1k_persona_description/`)
- Validate that the converted UserInfo objects produce sensible system prompts
- Test with 5–10 agents against OpenAI API locally

### Phase 2: Build graph + run simulation

- Start with a small run (50 agents, 10 timesteps, OpenAI API)
- Validate that agents take diverse actions consistent with their personas
- Scale to 1,000 agents on Greenland with vLLM

### Phase 3: Analyze and report

- Build the trace analyzer
- Verify persona-conditioned behavioral differences exist (the core research question)
- Generate reports that feed back into MatrAIx's Application team evaluation

---

## Dev vs. Production Configuration

| Setting | Dev (local) | Production (Greenland) |
|---------|-------------|------------------------|
| Agents | 10–50 | 1,000–10,000+ |
| LLM backend | OpenAI API (`gpt-4o-mini`) | vLLM (Llama-3-8B on 8x A100) |
| Timesteps | 5–10 | 50–100 |
| Semaphore | 10 | 128 |
| Activation probability | 1.0 (all agents act) | 0.05–0.10 |
| Database | `./data/dev.db` | `/tmp/instance_storage/simulation.db` |
| Recsys | `random` | `twitter` or `twhin-bert` |

---

## Dependencies to Install

```bash
# Core OASIS
pip install camel-oasis  # or: pip install camel-ai==0.2.78

# For personalized recsys
pip install sentence-transformers torch

# For network analysis
pip install igraph networkx

# For vLLM inference (Greenland only)
pip install vllm

# MatrAIx persona loading
pip install pyyaml
```

---

## Open Questions

1. **Big Five → MBTI**: Should we patch OASIS to accept Big Five directly in the system prompt instead of converting? This preserves more persona fidelity.
2. **Persona richness**: OASIS system prompts are short (~100 words). Should we inject the full MatrAIx persona description or a compressed version?
3. **Action space**: Full 29 actions or restricted set for initial experiments? Full set is more realistic but harder to analyze.
4. **Evaluation**: What specific emergent behaviors validate that personas are working? (e.g., introverts post less, risk-averse users don't repost controversial content)
5. **Scale target**: Start with 1,000 agents and scale up, or go straight to 10K on Greenland?
