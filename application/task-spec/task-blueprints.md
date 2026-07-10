# Task blueprints — visual maps

Use this page when the prose specs feel dense. It answers one question:

> **What must I author, what can I add later, and what is platform-owned or
> reference-only?**

Legend used in every diagram:

| Label | Meaning | Your action |
|---|---|---|
| **REQUIRED** | Ship without this and the task is incomplete | **You write it** in your task folder |
| **OPTIONAL** | Improves debrief quality or scenario richness | **You add when the study needs it** |
| **PLATFORM** | Runtime, harness, or job rollup | **Do not author** — know it exists |
| **REFERENCE** | Contracts, examples, canonical tasks | **Copy and lookup** — do not reinvent |

---

## Ecosystem — the whole spec at a glance

```mermaid
flowchart TB
  subgraph YOU ["🧑‍💻 YOU — task contributor"]
    direction TB
    Y1["Pick type: survey · chatbot · web · os-app"]
    Y2["Author scenario<br/>instruction.md + input/*"]
    Y3["Write verifier tests/<br/>→ structured_output.json"]
    Y4["Stub reporting.json<br/>(+ rules if you want Layer 2)"]
    Y1 --> Y2 --> Y3 --> Y4
  end

  subgraph TASK ["📁 application/tasks/&lt;your-task&gt;/"]
    direction TB
    T_REQ["REQUIRED: task.toml · instruction.md · tests/ · reporting.json"]
    T_OPT["OPTIONAL: input/* extras · self_report_schema.yaml"]
  end

  subgraph PLATFORM ["⚙️ PLATFORM — automatic"]
    direction TB
    P1["Persona injection<br/>persona/datasets/"]
    P2["Runtime / harness<br/>environment/task-environments/"]
    P3["Trial artifacts<br/>transcript · traces · results"]
    P4["Job aggregation<br/>aggregation.json · Runs UI"]
  end

  subgraph REF ["📚 REFERENCE — lookup & copy"]
    direction TB
    R1["task-spec/&lt;type&gt;/README.md"]
    R2["*.example.json templates"]
    R3["example-* canonical task"]
    R4["structured-output-quick-reference.md"]
  end

  YOU --> TASK
  TASK -->|"one trial"| PLATFORM
  Y3 -->|"facts per trial"| P4
  Y4 -.->|"optional Layer 2"| P4
  REF -.->|"copy patterns"| YOU
```

**Read the arrows:**

1. **You** pick a type and fill the task folder.
2. **Platform** runs personas, collects harness artifacts, rolls up jobs.
3. **Reference** docs tell you *which* facet keys and file shapes to copy — they
   are not files you commit per task.

---

## One trial → one job (responsibility split)

```mermaid
flowchart LR
  subgraph trial ["ONE TRIAL"]
    direction TB
    A1["REQUIRED<br/>instruction + input"]
    A2["PLATFORM<br/>agent + runtime artifacts"]
    A3["REQUIRED<br/>tests/ verifier"]
    A4["REQUIRED output<br/>structured_output.json"]
    A1 --> A2 --> A3 --> A4
  end

  subgraph job ["ONE JOB = many trials"]
    direction TB
    B1["PLATFORM reads all<br/>structured_output.json"]
    B2["OPTIONAL<br/>your reporting.json rules"]
    B3["PLATFORM writes<br/>aggregation.json"]
    B1 --> B3
    B2 -.-> B3
  end

  A4 --> B1
```

| Output | Who writes | Required? |
|---|---|---|
| `instruction.md`, `input/*` | You | Yes |
| Harness artifacts (transcript, traces, …) | Platform | — |
| `verifier/structured_output.json` | You (verifier) | Yes |
| `reporting.json` empty stub | You | Yes (stub is enough) |
| `reporting.json` LLM rules | You | Optional |
| `aggregation.json` | Platform | — |

---

## Survey blueprint

**Canonical copy-from:** `application/tasks/example-survey_product-feedback`  
**Contract:** [survey/README.md](survey/README.md)

```mermaid
flowchart TB
  subgraph folder ["YOUR task folder"]
    direction TB

    subgraph S_REQ ["REQUIRED — you author"]
      direction LR
      s_inst["instruction.md"]
      s_toml["task.toml"]
      s_q["input/questionnaire.yaml"]
      s_out["input/output_schema.md"]
      s_test["tests/"]
      s_rep["reporting.json"]
    end

    subgraph S_OPT ["OPTIONAL — consider"]
      direction LR
      s_ctx["input/context.md"]
      s_rep2["reporting.json<br/>contextRules"]
    end
  end

  subgraph S_PLAT ["PLATFORM — do not author"]
    direction LR
      s_rt["shared-survey-form runtime"]
      s_traj["survey trajectory appended"]
      s_agg["aggregation Layer 1"]
  end

  subgraph S_REF ["REFERENCE — copy & lookup"]
    direction LR
      s_ex["survey/*.example.json"]
      s_cheat["structured-output-quick-reference § Survey"]
  end

  S_REQ --> S_PLAT
  s_test -->|"structured_output.json"| s_agg
  S_REF -.-> folder
```

| Verifier must emit | Priority |
|---|---|
| `question_response` per question | **Required** |
| `trial_summary` | **Required** |
| Layer 2 summarize `reason` by `response` | Optional in `reporting.json` |

---

## Chatbot blueprint

**Canonical copy-from:** `application/tasks/recommender-agent_chat_api`  
**Contract:** [chatbot/README.md](chatbot/README.md) · harness: [chatbot/eval_artifacts.md](chatbot/eval_artifacts.md)

```mermaid
flowchart TB
  subgraph folder ["YOUR task folder"]
    direction TB

    subgraph C_REQ ["REQUIRED — you author"]
      direction LR
      c_inst["instruction.md"]
      c_toml["task.toml"]
      c_yaml["input/chatbot.yaml"]
      c_test["tests/"]
      c_rep["reporting.json"]
    end

    subgraph C_OPT ["OPTIONAL — consider"]
      direction LR
      c_ctx["input/context.md"]
      c_proto["input/protocol.md"]
      c_self["input/self_report_schema.yaml"]
      c_rep2["reporting.json rules"]
    end
  end

  subgraph C_PLAT ["PLATFORM — do not author per task"]
    direction LR
      c_tx["transcript.json"]
      c_app["application_result.json"]
      c_side["chat sidecar runtime"]
  end

  subgraph C_REF ["REFERENCE — copy & lookup"]
    direction LR
      c_ex["chatbot/*.example.json"]
      c_art["eval_artifacts.md"]
  end

  C_REQ --> C_PLAT
  c_self -.->|"user_feedback.json"| c_test
  C_REF -.-> folder
```

| Verifier context | Priority |
|---|---|
| `task_outcome` | **Required** |
| `conversation_summary` | Strongly recommended |
| `user_feedback` | Recommended when `self_report_schema.yaml` exists |
| `policy_and_trust`, `coordination` | Optional depth |

**Do not** create per-task `output_schema.md` for chatbot — platform owns the
harness artifacts listed in `eval_artifacts.md`.

---

## Web blueprint

**Canonical copy-from:** `application/tasks/example-web-playwright_quote-choice`  
**Contract:** [web/README.md](web/README.md) · shared core: [shared-core-metrics.md](shared-core-metrics.md)

```mermaid
flowchart TB
  subgraph folder ["YOUR task folder"]
    direction TB

    subgraph W_REQ ["REQUIRED — you author"]
      direction LR
      w_inst["instruction.md<br/>(includes result JSON schema)"]
      w_toml["task.toml"]
      w_test["tests/"]
      w_rep["reporting.json"]
    end

    subgraph W_OPT ["OPTIONAL — consider"]
      direction LR
      w_self["input/self_report_schema.yaml"]
      w_rep2["reporting.json rules"]
      w_dec["decision contexts in verifier"]
    end
  end

  subgraph W_PLAT ["PLATFORM — do not author"]
    direction LR
      w_br["browser / computer-use runtime"]
      w_trace["browser trace"]
  end

  subgraph W_REF ["REFERENCE — copy & lookup"]
    direction LR
      w_core["shared_core_metric_contract.example.json"]
      w_ex["web/*_structured_output.example.json"]
      w_ex2["web/*_reporting.example.json"]
  end

  W_REQ --> W_PLAT
  W_REF -.-> folder
```

Web tasks use **two verifier layers**:

1. **Shared core** (`task_outcome`, `side_effects`, `user_feedback`, …) — same
   keys as os-app → [shared-core-metrics.md](shared-core-metrics.md)
2. **Web layer** (`decision`, `decision_process`, `web_interaction`, …) — for
   browse/choose scenarios

| Context | Priority |
|---|---|
| `task_outcome` | **Required** |
| `decision` + `decision_process` | **Required** for browse/choose tasks |
| `goal_component`, `side_effects`, `user_feedback` | Strongly recommended |
| `web_interaction`, `experience` | Optional depth |

**No** `input/output_schema.md` — put the submission JSON schema inline in
`instruction.md`.

---

## OS / app blueprint

**Canonical copy-from:** `application/tasks/example-computer-use-ios_photo-access-review`  
**Contract:** [os-app/README.md](os-app/README.md) · shared core: [shared-core-metrics.md](shared-core-metrics.md)

```mermaid
flowchart TB
  subgraph folder ["YOUR task folder"]
    direction TB

    subgraph O_REQ ["REQUIRED — you author"]
      direction LR
      o_inst["instruction.md<br/>(includes result JSON schema)"]
      o_toml["task.toml"]
      o_test["tests/"]
      o_rep["reporting.json"]
    end

    subgraph O_OPT ["OPTIONAL — consider"]
      direction LR
      o_self["input/self_report_schema.yaml"]
      o_rep2["reporting.json rules"]
      o_pers["persona_alignment contexts"]
    end
  end

  subgraph O_PLAT ["PLATFORM — do not author"]
      direction LR
      o_cu["computer-use / native app runtime"]
      o_local["local artifacts on disk"]
  end

  subgraph O_REF ["REFERENCE — copy & lookup"]
      direction LR
      o_core["shared_core_metric_contract.example.json"]
      o_ex["os-app/*_structured_output.example.json"]
  end

  O_REQ --> O_PLAT
  O_REF -.-> folder
```

OS/app emphasizes **outcome-based verification** (final state, not action
sequence). Reuse the **same shared core** as web; add scenario-specific contexts
(local artifact checks, cross-app handoff) on top — do not rename shared facet
keys.

| Context | Priority |
|---|---|
| `task_outcome` | **Required** |
| `goal_component`, `side_effects` | Strongly recommended |
| `user_feedback`, `persona_alignment` | When the study needs them |
| `infeasibility` | When tasks can be intentionally blocked |

---

## Which doc when? (navigation map)

```mermaid
flowchart TD
  START([I am making a task]) --> Q1{What phase?}

  Q1 -->|Pick type| BP[task-blueprints.md<br/>this page]
  Q1 -->|Write files| AB[authoring-bundle.md]
  Q1 -->|Verifier / facets| SO[structured-output-quick-reference.md]
  Q1 -->|Batch reporting| RE[reporting-and-evaluation.md]
  Q1 -->|web vs os-app| SC[shared-core-metrics.md]

  BP --> TYPE["&lt;type&gt;/README.md"]
  TYPE --> CANON["example-* canonical task"]
  SO --> EX["*.example.json"]
  RE --> EX
```

| I need to… | Open |
|---|---|
| See the big picture & required vs optional | **This page** |
| Onboard step-by-step | [README.md](README.md) |
| File tree for my type | [authoring-bundle.md](authoring-bundle.md) |
| Context/facet cheat sheet | [structured-output-quick-reference.md](structured-output-quick-reference.md) |
| How aggregation works | [reporting-and-evaluation.md](reporting-and-evaluation.md) |
| Copy-paste commands | [../tasks/README.md](../tasks/README.md) |

---

## Minimum viable task (all types)

Every type ships this skeleton — everything else is optional or reference:

```text
application/tasks/<your-task>/
├── task.toml              REQUIRED
├── instruction.md         REQUIRED
├── tests/                 REQUIRED → structured_output.json
├── reporting.json         REQUIRED (empty contextRules OK)
└── input/                 type-specific REQUIRED files inside
```

If you only do the **REQUIRED** column in your type blueprint above, the task
runs and Layer 1 batch stats appear in Runs. Add **OPTIONAL** pieces when the
product question needs richer debrief or persona self-report.
