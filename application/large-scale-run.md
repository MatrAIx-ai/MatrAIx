# Large-Scale Run — Representative Tasks × 1000 Personas

## The task

Run **all representative tasks** for the Large-scale run, listed in the
planning spreadsheet:

https://docs.google.com/spreadsheets/d/1CiXWXKKs9AxyqJbq1ZyBYqZj4-6RxRPPWzlB7zVzRyk/edit?gid=0#gid=0

Right now the scope is **rows 2-7**, but **rows 4, 5, and 6 are not
ready yet**.

All tasks live in the MatrAIx codebase:

https://github.com/MatrAIx-ai/MatrAIx

**Everything should be run on `main`.**

## Personas

Run each task with the **existing cohort of 1000 persona profiles** stored in
the task's source folder in the
[MatrAIx2026/Demo_Application_Data](https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main)
dataset. Open the matching type and task folder, then download its
`Persona Profiles/` folder. Do not replace this cohort with personas from
`persona/datasets/bench-dev-sample`, and do not generate a new cohort from the
task's `persona_strategy.json`.

For the **Notion pricing plan-comparison web task**, reuse the 1000 profiles
from the GitHub pricing plan-fit task:

https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main/Type%203%20-%20Website/web-github-pricing_plan-fit/Persona%20Profiles

This is the authoritative input cohort for the Notion run. Preserve the
downloaded filenames and provenance files. Before running, verify that the
folder contains exactly 1000 numbered `persona_*.yaml` files; keep
`manifest.json`, `persona.jsonl`, and `SOURCE_README.md` with the cohort for
auditing.

For other representative tasks, use the same procedure: select the matching
type folder, open the designated source task folder, and use the cohort inside
its `Persona Profiles/` folder. If the planning spreadsheet does not identify
the source task folder, confirm it with the application owner before running.

## Running

Run each task following the specification in the codebase. You will need
to specify what model to use.

## Where to find what you need to save

Package the run artifacts produced by Harbor together with the exact downloaded
`Persona Profiles/` cohort used as input. Do not substitute profiles from a
different local directory when packaging the run. Record the Hugging Face
source URL and, when available, the source dataset revision in the run README.

## What to save

Save everything for each run to the HuggingFace dataset:

https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main

Place the `modelname_taskname` folder inside the existing folder on the
dataset's main that matches the task's type (for example
`Type 1 - Survey/`, `Type 2 - Chatbot/`, `Type 3 - Website/`,
`Type 4 - App/`), using this structure:

```
folder: <type folder>/modelname_taskname
├── Persona Profiles/         exact 1000-persona input cohort downloaded
│                             from the designated Hugging Face source folder,
│                             including its provenance and manifest files
├── artifact/                 all telemetries
├── report/                   (optional) reports generated
├── README                    a small description of the task and the
│                             configurations of the run, plus the persona
│                             source URL and dataset revision
└── persona_strategy.json
```

**Final note:** upload everything generated to
[MatrAIx2026/Demo_Application_Data](https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main)
on Hugging Face. Put each `modelname_taskname` folder under the matching task
type folder on the dataset's `main` branch (for example, `Type 1 - Survey/`,
`Type 2 - Chatbot/`, `Type 3 - Website/`, or `Type 4 - App/`).
