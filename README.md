# MatrAIx

MatrAIx is a modular benchmark and runtime stack for persona-conditioned
simulation. It keeps persona data, application scenarios, and execution
infrastructure separated so each piece can be reviewed, tested, and extended
without turning `main` into a raw migration snapshot.

The repository is organized around three contribution modules plus repo-local
tooling:

```text
persona/       Persona schemas, datasets, curation pipelines, and persona bench tasks.
application/   Product and research scenarios that consume personas.
environment/   Runtime, agents, job recipes, viewer, and execution infrastructure.
apps/          Repo-local tool frontends paired with runtime APIs.
```

The rule of thumb is simple:

- `persona/` defines who the simulated user is and how persona adherence is
  evaluated.
- `application/` defines what scenario, product, or workflow the simulated user
  interacts with.
- `environment/` defines how the simulation runs, logs, and verifies work.
- `apps/` contains developer-facing tool frontends, currently the viewer UI for
  `harbor view`.

Shared libraries may live under `packages/` when they are genuinely reusable.
The root Python distribution and compatibility namespace are currently named
`personabench`; do not rename imports as part of documentation-only cleanup.

## Repository State

This clean `main` keeps the runnable and reviewable parts of MatrAIx under
stable module boundaries:

- `persona/`: persona schema, curation utilities, sample datasets, persona
  grounding tasks, bench tasks, reporting, and validators.
- `application/`: application task definitions, reporting code, and curated
  recipe generation helpers.
- `environment/`: Harbor runtime, persona agents, adapter foundation, SimpleQA
  adapter, curated job recipes, and environment docs.
- `apps/viewer/`: the repo-local viewer frontend for inspecting Harbor jobs.
- `packages/`: optional reusable packages such as `harbor-langsmith` and
  `rewardkit`.

Historical run outputs, generated datasets, large fixtures, screenshots,
recordings, raw dumps, and migration snapshots stay outside git. External data
dependencies and upload TODOs are tracked in
[the artifact handoff checklist](migration/matraix/README.md).

## Quick Start

```bash
uv venv --python 3.12
uv pip install -e .
uv pip install pytest pytest-asyncio
uv pip install -e packages/harbor-langsmith
uv pip install -e packages/rewardkit
uv pip install -e environment/adapters/simpleqa
uv run pytest tests/ packages/harbor-langsmith/tests/ packages/rewardkit/tests/
uv run ruff check .
```

Run a local smoke job that does not need model credentials:

```bash
uv run harbor run -c configs/jobs/example-job-recipe/harbor-smoke-local.yaml
```

Run the curated persona application example after setting the required model
API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-survey-local.yaml
```

More setup, optional package, adapter, viewer, and artifact details are in
[Running MatrAIx](docs/running.md).

## Persona Data

Persona schema, datasets, curation pipelines, collaborator packages, and
artifact handoff guidance live under [persona/](persona/README.md).

Useful entry points:

- [Existing-data curation](persona/curation/existing_data/README.md) documents
  the Wikipedia and Amazon package-generation flow.
- `persona/curation/existing_data/scripts/make_package.py` is the preferred
  owner-facing package generator for both `--source wiki` and
  `--source amazon`.
- [Artifact handoff](migration/matraix/README.md) lists large generated data
  that stays outside `main` until uploaded externally.
- Real wiki/Amazon DBs, manifests, raw histories, and other large data
  dependencies are external artifacts with `TODO` URL slots; do not hardcode
  local machine paths in code or docs.

## Research Notes

MatrAIx research notes are kept as module-specific working references:

- [Persona related work](docs/research/persona-related-work.md)
- [Behavior-grounded personas](docs/research/behavior-grounded-personas.md)
- [AutoPersona causal schema-learning proposal](docs/research/autopersona.md)
- [Application related work](docs/research/application-related-work.md)
- [Application areas taxonomy](docs/research/application-areas-taxonomy.md)
- [Application domain benchmark catalog](docs/research/application-domain-benchmark-catalog.md)
- [Environment related work](docs/research/environment-related-work.md)

The environment note is intentionally thinner than the persona and application
notes because the source material had fewer complete environment entries.

Start here:

- [Architecture](docs/architecture.md)
- [Running MatrAIx](docs/running.md)
- [Research notes](docs/research/README.md)
- [Contributing](CONTRIBUTING.md)

Migration provenance is available under [migration/matraix/](migration/matraix/)
and [docs/migration/](docs/migration/) for reviewers who need source history.
