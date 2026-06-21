# OASIS Environment — Open Agent Social Interaction Simulations

> Part of [MatrAIx](../../README.md) Environment team. This directory integrates [OASIS](https://github.com/camel-ai/oasis) (Open Agent Social Interaction Simulations with One Million Agents) as a multi-agent social simulation environment.

**Paper**: [arXiv:2411.11581](https://arxiv.org/abs/2411.11581)
**Upstream**: https://github.com/camel-ai/oasis
**License**: Apache 2.0

---

## Overview

OASIS is a scalable social media simulation framework where LLM-powered agents act as users on Twitter-like and Reddit-like platforms. It enables studies of large-scale social phenomena: information spreading, group polarization, herd behavior, and recommendation system effects.

Key capability: simulate up to **1 million agents** by combining activation probability gating, distributed vLLM inference across 72+ endpoints, and sparse per-timestep participation (~1% of agents act each step).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         OasisEnv                                 │
│  (PettingZoo-style: make() → reset() → step() → close())       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────────────────────────┐  │
│  │  AgentGraph   │         │         Platform                 │  │
│  │  (igraph /    │◄═══════►│  (async event loop)              │  │
│  │   Neo4j)      │ Channel │                                  │  │
│  │              │  (async  │  ┌────────────┐  ┌───────────┐  │  │
│  │  SocialAgent │  Queue)  │  │   SQLite   │  │  RecSys   │  │  │
│  │  SocialAgent │         │  │  (16 tables)│  │ (4 algos) │  │  │
│  │  SocialAgent │         │  └────────────┘  └───────────┘  │  │
│  │  ...         │         │                                  │  │
│  └──────────────┘         └──────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────┐         ┌──────────────────────────────────┐  │
│  │ LLM Backend  │         │         Clock                    │  │
│  │ (vLLM / API) │         │  (time dilation, discrete steps) │  │
│  └──────────────┘         └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow (Single Agent Action)

```
Agent.perform_action_by_llm()
  → SocialEnvironment.to_text_prompt()     # Build observation from feed
    → SocialAction.refresh()               # Send refresh via Channel
      → Channel → Platform event loop      # Platform queries SQLite
      → Channel ← recommended + following posts returned
  → Agent.astep(user_msg)                  # LLM call (function calling)
  → LLM returns tool_calls                 # Structured action selection
  → SocialAction.<method>()               # Execute chosen action via Channel
    → Platform processes action in DB      # State update
```

---

## Core Components

### 1. OasisEnv (`oasis/environment/env.py`)

The main simulation environment. PettingZoo-inspired API:

```python
import oasis

env = oasis.make(
    agent_graph=agent_graph,
    platform=oasis.DefaultPlatformType.TWITTER,  # or REDDIT
    database_path="./simulation.db",
    semaphore=128,  # max concurrent LLM calls
)

await env.reset()   # Start platform event loop, sign up all agents
await env.step(actions)  # One timestep: update recsys → agents act → advance clock
await env.close()   # Shutdown
```

Each `step()`:
1. Updates the recommendation table for all users
2. Creates concurrent tasks for all active agents (gated by asyncio.Semaphore)
3. Executes via `asyncio.gather`
4. Advances the simulation clock

### 2. SocialAgent (`oasis/social_agent/agent.py`)

Extends CAMEL's `ChatAgent`. Each agent has:
- **Persona** (UserInfo): name, bio, profile dict (MBTI, age, gender, interests)
- **SocialEnvironment**: builds the observation prompt (feed posts)
- **SocialAction**: 29 action methods exposed as OpenAI function tools
- **LLM backend**: one or more model instances (load-balanced across vLLM endpoints)

The LLM sees all available actions as tool definitions and decides which to invoke based on the persona system prompt + current feed observation.

### 3. Platform (`oasis/social_platform/platform.py`)

Async event loop that processes all agent actions sequentially:
- Receives actions via Channel (async queue with UUID-keyed responses)
- Executes SQL operations against SQLite
- Returns results back via Channel
- Single-threaded for database consistency (agents are concurrent via asyncio)

### 4. AgentGraph (`oasis/social_agent/agent_graph.py`)

Directed graph representing FOLLOW relationships:
- **igraph backend** (default): fast for up to ~100K nodes
- **Neo4j backend**: for persistence and large-scale visualization
- Updated dynamically by follow/unfollow actions

For 1M agents, replaced with a plain Python list (igraph overhead too high).

### 5. Recommendation System (`oasis/social_platform/recsys.py`)

Four algorithms control what each agent sees in their feed:

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| `random` | Random sampling of posts | Baseline |
| `reddit` | Reddit hot-score: `sign * log10(votes) + epoch/45000` | Reddit simulation |
| `twitter` | `paraphrase-MiniLM-L6-v2` cosine similarity (user bio ↔ post) | Small-scale Twitter |
| `twhin-bert` | `Twitter/twhin-bert-base` + time decay + like history | 1M-scale Twitter |

The recommendation system is the mechanism that shapes information flow and emergent behavior in the simulation.

---

## Agent Persona Format

### Schema v1 (structured)

```json
{
    "realname": "James Miller",
    "username": "millerhospitality",
    "bio": "Passionate about hospitality management",
    "persona": "James is a seasoned professional in hotel management...",
    "age": 40,
    "gender": "male",
    "mbti": "ESTJ",
    "country": "UK",
    "profession": "Hospitality & Tourism",
    "interested_topics": ["Economics", "Business"]
}
```

### UserInfo System Prompt (what the LLM sees)

```
# OBJECTIVE
You're a Twitter user, and I'll present you with some tweets.
After you see the tweets, choose some actions from the following functions.

# SELF-DESCRIPTION
Your actions should be consistent with your self-description and personality.
Your name is James Miller.
Your have profile: James is a seasoned professional in hotel management...

# RESPONSE METHOD
Please perform actions by tool calling.
```

### Persona Generation (at scale)

The `generator/` scripts create diverse profiles using:
- Weighted random sampling for age distribution (13-17: 6.6%, 18-24: 17.1%, 25-34: 38.5%, 35-49: 20.7%, 50+: 17.1%)
- 16 MBTI types with realistic distribution
- 16 profession categories
- Combinatorial topic interests (9 topics, 2 per user)
- LLM-generated detailed persona text via RAG-based generation
- ThreadPoolExecutor (50 workers) for parallel profile creation

---

## Action Space (29 actions)

### Post Actions
| Action | Description |
|--------|-------------|
| `create_post(content)` | Publish a new post |
| `repost(post_id)` | Share an existing post |
| `quote_post(post_id, content)` | Share with added commentary |
| `like_post(post_id)` | Like a post |
| `unlike_post(post_id)` | Remove like |
| `dislike_post(post_id)` | Dislike a post |
| `undo_dislike_post(post_id)` | Remove dislike |
| `report_post(post_id, reason)` | Report content |

### Comment Actions
| Action | Description |
|--------|-------------|
| `create_comment(post_id, content)` | Comment on a post |
| `like_comment(comment_id)` | Like a comment |
| `unlike_comment(comment_id)` | Remove comment like |
| `dislike_comment(comment_id)` | Dislike a comment |
| `undo_dislike_comment(comment_id)` | Remove comment dislike |

### Social Actions
| Action | Description |
|--------|-------------|
| `follow(user_id)` | Follow a user |
| `unfollow(user_id)` | Unfollow a user |
| `mute(user_id)` | Mute a user |
| `unmute(user_id)` | Unmute a user |

### Discovery
| Action | Description |
|--------|-------------|
| `refresh()` | Refresh feed (get recommended + following posts) |
| `search_posts(query)` | Search posts by keyword |
| `search_user(query)` | Search users by name |
| `trend()` | Get trending topics |

### Meta
| Action | Description |
|--------|-------------|
| `do_nothing()` | Explicitly do nothing this turn |

Agents select actions via **OpenAI function calling** — the LLM sees all available actions as tool definitions and returns structured `tool_calls`.

---

## Database Schema (SQLite, 16 tables)

| Table | Key Columns |
|-------|-------------|
| `user` | user_id, agent_id, user_name, name, bio, created_at, num_followings, num_followers |
| `post` | post_id, user_id, original_post_id, content, quote_content, created_at, num_likes, num_dislikes, num_shares |
| `follow` | follow_id, follower_id, followee_id, created_at |
| `like` | like_id, user_id, post_id, created_at |
| `dislike` | dislike_id, user_id, post_id, created_at |
| `comment` | comment_id, post_id, user_id, content, created_at, num_likes, num_dislikes |
| `comment_like` | comment_like_id, user_id, comment_id, created_at |
| `comment_dislike` | comment_dislike_id, user_id, comment_id, created_at |
| `mute` | mute_id, user_id, mutee_id |
| `rec` | user_id, post_id (recommendation buffer, rebuilt each timestep) |
| `trace` | trace_id, user_id, action, info (JSON), created_at |
| `report` | report_id, user_id, post_id, reason |
| `product` | product_id, product_name, sales |
| `chat_group` | group_id, group_name |
| `group_member` | group_id, user_id |
| `group_message` | message_id, group_id, user_id, content, created_at |

All actions are recorded in the `trace` table with full JSON info for analysis.

---

## Scaling to 1 Million Agents

### Key Optimizations

1. **Activation probability gating**: Each agent has an hourly `active_threshold` (e.g., 0.01). Only ~1% of agents act per timestep, so ~10,000 LLM calls per step from 1M agents.

```python
if random.random() < agent.active_threshold[hour % 24]:
    tasks.append(agent.perform_action_by_llm())
```

2. **Distributed vLLM inference**: 72 endpoints across 3 GPU servers (24 ports each), running Llama-3-8B-Instruct. Random scheduling distributes load.

3. **Reduced action space**: 1M simulations use only 4 actions: `do_nothing`, `repost`, `like_post`, `follow`.

4. **List-based agent storage**: AgentGraph replaced with a plain list (igraph overhead too high at 1M).

5. **Bulk database operations**: `_execute_many_db_command()` for batch inserts of users, follows, posts.

6. **Async concurrency**: `asyncio.Semaphore(128)` limits concurrent LLM calls while keeping throughput high.

### Infrastructure Requirements (1M scale)

| Resource | Specification |
|----------|--------------|
| GPU servers | 3+ machines with GPUs (for vLLM) |
| vLLM endpoints | 72 (24 per server) |
| Model | Meta-Llama-3-8B-Instruct |
| Orchestration | Single machine (Python asyncio) |
| Database | SQLite (can use `:memory:` for speed) |
| RAM | 64GB+ on orchestration node |

### Infrastructure for Smaller Experiments

| Scale | LLM Backend | Hardware |
|-------|-------------|----------|
| 10-100 agents | OpenAI API / single vLLM | Any machine + API key |
| 1K-10K agents | 1-4 vLLM endpoints | 1 GPU server |
| 100K agents | 8-16 vLLM endpoints | 1-2 GPU servers |
| 1M agents | 72 vLLM endpoints | 3+ GPU servers |

---

## Configuration

### YAML Format (for large-scale experiments)

```yaml
data:
  db_path: data/db/simulation.db
  csv_path: data/agent_profiles.csv

simulation:
  num_timesteps: 60
  clock_factor: 60
  recsys_type: twhin-bert    # random | reddit | twitter | twhin-bert
  available_actions:
    - do_nothing
    - repost
    - like_post
    - create_post
    - follow

inference:
  model_type: llama-3
  model_path: models/Meta-Llama-3-8B-Instruct
  stop_tokens: ["<|eot_id|>", "<|end_of_text|>"]
  server_url:
    - host: 10.140.1.129
      ports: [8002, 8003, 8004, 8005]
```

### Programmatic API

```python
import oasis

# Create agent graph with personas
agent_graph = oasis.AgentGraph()
for profile in profiles:
    user_info = oasis.UserInfo(
        name=profile["realname"],
        user_name=profile["username"],
        description=profile["bio"],
        profile={"other_info": {"user_profile": profile["persona"], ...}}
    )
    agent = oasis.SocialAgent(user_info=user_info, model=llm_model)
    agent_graph.add_agent(agent)

# Create environment
env = oasis.make(
    agent_graph=agent_graph,
    platform=oasis.DefaultPlatformType.TWITTER,
    database_path="./sim.db",
    semaphore=128,
)

# Run simulation
await env.reset()
for t in range(num_timesteps):
    actions = {agent: oasis.LLMAction() for _, agent in env.agent_graph.get_agents()}
    await env.step(actions)
await env.close()
```

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `camel-ai` | 0.2.78 | Multi-agent framework (ChatAgent, ModelFactory, tool calling) |
| `igraph` | 0.11.6 | In-memory directed graph for social network |
| `neo4j` | 5.23.0 | Optional graph database backend |
| `sentence-transformers` | 3.0.0 | Embedding models for personalized recsys |
| `torch` | — | GPU-accelerated embeddings and similarity |
| `pandas` | 2.2.2 | Agent data loading |
| `vllm` | — | Distributed LLM inference at scale |
| Python | >=3.10, <3.12 | Required version range |

Install:
```bash
pip install camel-oasis
# or from source:
git clone https://github.com/camel-ai/oasis && cd oasis && pip install -e .
```

---

## Relevance to MatrAIx

OASIS maps directly to MatrAIx's Environment team goals:

| MatrAIx Concept | OASIS Implementation |
|-----------------|---------------------|
| Persona injection | `UserInfo` → system prompt with bio, MBTI, age, interests |
| Environment type | Multi-agent social (Twitter/Reddit platforms) |
| Telemetry/trace | SQLite `trace` table records every action with full JSON |
| Evaluation | Post-hoc analysis of traces for polarization, information spread |
| Scalability | 1M agents via activation gating + distributed inference |
| Recommendation | 4 algorithms controlling information exposure |

### Integration Plan

This environment extends MatrAIx beyond single-agent tasks (survey, chatbot, web) into **multi-agent social simulation** where:
- MatrAIx personas become OASIS agents
- Social dynamics (follow, post, like, repost) emerge from persona-conditioned LLM decisions
- The recommendation system shapes information flow
- Traces feed into MatrAIx's telemetry and reporting pipeline

---

## References

- [OASIS Paper](https://arxiv.org/abs/2411.11581) — Xiong et al., 2024
- [CAMEL-AI Framework](https://github.com/camel-ai/camel) — Multi-agent foundation
- [vLLM](https://github.com/vllm-project/vllm) — High-throughput LLM serving
- [Twitter/twhin-bert-base](https://huggingface.co/Twitter/twhin-bert-base) — Twitter's production embedding model
