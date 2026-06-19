# Catalog-Backed RecBot Ranker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the InteRecAgent provider use the MatrAIx normalized recommendation catalog as its item universe and provide a native-like personalized ranking substitute when a catalog-aligned RecAI checkpoint is unavailable.

**Architecture:** The bridge keeps RecAI's planner, prompt, native action contract, `BaseGallery`, `CandidateBuffer`, lookup, hard filter, similarity filter, and map tools. MatrAIx adds a catalog-to-RecAI resource adapter and replaces only the checkpoint-dependent `RecModelTool` with a semantic profile ranker by default for catalog-backed runs.

**Tech Stack:** Python stdlib, NumPy, RecAI/InteRecAgent, existing MatrAIx `RecBotRequest` / `RecBotTurnResult` provider interface, `unittest`.

---

### Task 1: Catalog-To-RecAI Resource Adapter

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/catalog_resources.py`
- Test: `applications/recommendation_chatbot_eval/tests/test_catalog_resources.py`

- [ ] **Step 1: Write failing tests**

Test that a normalized JSONL catalog is converted into a RecAI-compatible resource directory containing:

- `settings.json`
- `item_info.csv`
- `table_col_desc.json`
- `item_sim.npy`

The generated CSV must use RecAI internal integer ids starting at 1, keep the original id in `external_id`, expose `title`, `tags`, `description`, `display_text`, and `visited_num`, and create a symmetric similarity matrix with an unused zero index.

- [ ] **Step 2: Run adapter tests and verify failure**

Run:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications.recommendation_chatbot_eval.tests.test_catalog_resources -v
```

Expected: import or attribute failure because `recbot.catalog_resources` does not exist yet.

- [ ] **Step 3: Implement adapter**

Implement:

- `RecAIResourceSpec`
- `load_catalog_items(path)`
- `ensure_recai_resource_dir(catalog_path, output_dir, domain)`

Use deterministic lexical cosine similarity over title, categories, description, and display text for `item_sim.npy`.

- [ ] **Step 4: Run adapter tests and verify pass**

Run the same test command and confirm it passes.

### Task 2: Semantic Profile Ranking Tool

**Files:**
- Create: `applications/recommendation_chatbot_eval/recbot/semantic_ranker.py`
- Test: `applications/recommendation_chatbot_eval/tests/test_semantic_ranker.py`

- [ ] **Step 1: Write failing tests**

Test that the substitute ranking tool:

- accepts the same `name`, `desc`, `item_corups`, `buffer`, and `rec_num` shape as RecAI `RecModelTool`,
- supports `schema=popularity`, `schema=similarity`, and `schema=preference`,
- fuzzy matches `prefer` / `unwanted` titles through the corpus,
- ranks candidates similar to liked items ahead of unrelated items,
- removes or demotes unwanted items,
- pushes ranked ids back into the candidate buffer,
- records a track entry.

- [ ] **Step 2: Run ranker tests and verify failure**

Run:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications.recommendation_chatbot_eval.tests.test_semantic_ranker -v
```

Expected: import or attribute failure because `recbot.semantic_ranker` does not exist yet.

- [ ] **Step 3: Implement ranker**

Implement `SemanticProfileRankingTool` with the RecAI tool contract:

```python
tool = SemanticProfileRankingTool(name, desc, item_corups, buffer, rec_num=100)
tool.run('{"schema":"preference","prefer":["The Batman"],"unwanted":["Saw"]}')
```

The default preference score should combine positive item-profile similarity, optional current-request similarity from `MATRAIX_CURRENT_USER_REQUEST`, popularity prior, and unwanted-item penalty.

- [ ] **Step 4: Run ranker tests and verify pass**

Run the same test command and confirm it passes.

### Task 3: Bridge Wiring

**Files:**
- Modify: `applications/recommendation_chatbot_eval/recbot/interecagent_bridge.py`
- Modify: `applications/recommendation_chatbot_eval/tests/test_interecagent_bridge.py`

- [ ] **Step 1: Write failing bridge tests**

Test that:

- `_prepare_imports` no longer requires RecAI's bundled `resources/<domain>` for catalog-backed mode.
- catalog-backed mode calls `ensure_recai_resource_dir`.
- catalog-backed mode creates RecAI native lookup/filter/similarity/map tools and `SemanticProfileRankingTool`.
- `run_turn` sets `MATRAIX_CURRENT_USER_REQUEST` before the agent runs.

- [ ] **Step 2: Run bridge tests and verify failure**

Run:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest applications.recommendation_chatbot_eval.tests.test_interecagent_bridge -v
```

Expected: failure because bridge still requires RecAI resources and always constructs `RecModelTool`.

- [ ] **Step 3: Implement bridge changes**

Add resource modes:

- `INTERECAGENT_RESOURCE_MODE=matraix_catalog` as default.
- `INTERECAGENT_RESOURCE_MODE=recai_resources` for old behavior.

Add ranking modes:

- `INTERECAGENT_RANKER_MODE=semantic_profile` as default in catalog mode.
- `INTERECAGENT_RANKER_MODE=native` for catalog-aligned native checkpoint use.

- [ ] **Step 4: Run bridge tests and verify pass**

Run the bridge test command and confirm it passes.

### Task 4: Interactive Agent Script And Docs

**Files:**
- Create: `applications/recommendation_chatbot_eval/scripts/chat_interecagent_movie.py`
- Modify: `applications/recommendation_chatbot_eval/scripts/smoke_interecagent_movie.py`
- Modify: `applications/recommendation_chatbot_eval/INTERECAGENT_PROVIDER.md`
- Modify: `applications/recommendation_chatbot_eval/README.md`

- [ ] **Step 1: Write or update CLI smoke behavior**

The interactive script should preserve messages across turns and call the provider for each user input:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python applications/recommendation_chatbot_eval/scripts/chat_interecagent_movie.py
```

It should default `INTERECAGENT_CATALOG_PATH` to the committed tiny movie fixture when unset.

- [ ] **Step 2: Update docs**

Document required environment variables:

- `INTERECAGENT_ROOT`
- `INTERECAGENT_PYTHON`
- `OPENAI_API_KEY`
- optional `INTERECAGENT_CATALOG_PATH`
- optional `INTERECAGENT_RANKER_MODE`

- [ ] **Step 3: Run full verification**

Run:

```sh
PYTHONPATH=applications/recommendation_chatbot_eval python -m unittest discover -s applications/recommendation_chatbot_eval/tests -v
python -m py_compile applications/recommendation_chatbot_eval/recbot/*.py applications/recommendation_chatbot_eval/scripts/*.py
jq empty applications/recommendation_chatbot_eval/schemas/catalog_item.schema.json
while IFS= read -r line; do printf '%s\n' "$line" | jq empty; done < applications/recommendation_chatbot_eval/samples/cmu_movie_summary_tiny.jsonl
```

Expected: all commands exit 0.
