# AppWorld API Task Interface

AppWorld tasks evaluate a persona-driven agent that completes a stateful
multi-application task through AppWorld-style APIs. BenchFlow hosts the agent and
returns both the final task artifact and the action trajectory.

## Task instruction

The task instruction describes the target AppWorld scenario, the available app
surface, and the final state the persona is trying to reach. The persona context
must be included in the prompt sent to the hosted agent so actions reflect the
simulated user's needs and preferences.

## Interaction protocol

The agent interacts through AppWorld API calls only. Each action should record
the target app, method, arguments, and any observation needed to understand the
next step. The hosted agent may inspect state, mutate app data, and check the
result through the same public task API surface.

## Task-specific environment

BenchFlow owns the AppWorld runtime for these tasks. MatrAIx sends the persona,
task metadata, config, and prompts to BenchFlow with `taskType=appworld`.
BenchFlow returns `appworld_result.json` and `trace.json` artifacts.

## Stop conditions

Runs stop when the agent emits a final answer, reaches the expected AppWorld
state, hits the task step or time limit, or the AppWorld runtime reports failure.
Incomplete or failed runs should still return a trace when possible.

## Artifacts

- `appworld_result.json`: final normalized task result.
- `trace.json`: ordered agent trajectory with API actions and raw runner data.
- Optional logs or diagnostics may be included by the BenchFlow runner.

## Evaluation contract

`appworld_result.json` must include:

- `task_id`: the AppWorld task identifier.
- `success`: whether the final state satisfies the task.
- `score`: normalized objective score from `0.0` to `1.0`.
- `outcome`: concise final state summary.
- `reason`: evaluator rationale or failure explanation.

`trace.json` must include an `events` list. Each event should include a step
number, source, message, and an `actions` list whose action names use
`appworld_api_call` for AppWorld API operations.
