# Contributing to MatrAIx

MatrAIx is built by three teams — **Persona**, **Environment**, and **Application**. This guide covers how to contribute: workflow (Issues, Discussions, PRs), where each team works in the repo, and the main contribution areas.

## Contribution flow

1. **Choose your team(s)** — read the three team docs below. One PR can touch multiple teams; tag every team involved.
2. **Open or pick an Issue** — Issues are for todos, task proposals, and bugs. The **creator** tags `team: persona|environment|application`. Either **assign yourself** and start work, or leave it open for someone else to claim in a comment.
3. **Log progress in Discussions** — Discussions are for your contribution history (design notes, experiments, weekly updates). Keep one long-lived thread; append dated posts so maintainers can review what you did over time. Do not use Issues for this.
4. **One Issue per PR** — every PR must link the Issue it implements (`Fixes #123`). Drive-by PRs without a linked Issue are closed. You may also link your Discussion thread in the PR body.
5. **Write the PR clearly** — what changed, why, how you tested. Link the Issue; use `git commit -s`.
6. **Merge** — CI must pass. GitHub auto-labels the PR and requests reviewers ([CODEOWNERS](../.github/CODEOWNERS)). At least **one** approval from an admin or the relevant team reviewer is required before merge.

Org members: branch on this repo. Everyone else: **fork** and PR from your fork.

Questions: [Discord](https://discord.gg/vruP88PTZ).

### Teams — paths, plan, where to start

| Team | Main paths | Plan | Start here |
|------|------------|------|------------|
| **Persona** | `persona/` | [personas/PLAN.md](personas/PLAN.md) | [personas/getting-started.md](personas/getting-started.md) |
| **Environment** | everything else (Harbor runtime, agents, jobs, viewer, infra, …) | [environments/PLAN.md](environments/PLAN.md) | [environments/README.md](environments/README.md) |
| **Application** | `application/` | [applications/PLAN.md](applications/PLAN.md) | [applications/getting-started.md](applications/getting-started.md) |

---

## Contributing points

**How contribution is recognized**

- **Task work** — Persona bench tasks, Application tasks, and runnable task examples/pipelines: **count and quality** of merged work in the repo. **Only merged task PRs count**; detailed quality standards are still being finalized (verifiers, metrics, reproducibility, and review expectations will follow).
- **Everything else** — research, schema, datasets, infra, dashboards, agents, etc.: **effort** as reviewed by the **team reviewer** and **maintainers**, primarily from your **Discussion** thread and linked PRs.

| Team | Contribution area | Recognized by |
|------|-------------------|---------------|
| **Persona** | Persona survey and related-work research | Effort |
| | Dataset curation | Effort |
| | Dimension and persona schema | Effort |
| | Persona attributes counterfactual filter | Effort |
| | Persona bench task design (persona grounding) | Effort |
| | Persona bench task curation | Task count & quality |
| **Environment** | Environment infrastructure | Effort |
| | Persona task examples and pipeline | Task count & quality |
| | Application task examples and pipeline | Task count & quality |
| | Viz / dashboard for persona runs | Effort |
| | All-in-one viz / dashboard for application tasks | Effort |
| | Social-oriented environment sandbox and middleware for Harbor | Effort |
| | Contributing agent that scans task quality | Effort |
| **Application** | Research or demo development | Effort |
| | Application task development — environment dependencies, persona cohort, isolated app servers, persona- and application-side metrics **(key)**, metrics on dashboard ([task-guide](applications/task-guide.md)) | Task count & quality |

---

## Basics

- **License:** Apache 2.0. No confidential data, PII, or secrets in the repo.
- **Setup:** `uv sync` — see [applications/getting-started.md §2](applications/getting-started.md#2-install-uv-clone-and-sync).
