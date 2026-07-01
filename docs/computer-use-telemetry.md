# Computer-use system telemetry

MatrAIx records **system-side telemetry** alongside agent trajectories for `use-computer` trials on **macOS** and **iOS Simulator**. The goal is ground-truth OS signals (notification settings, Focus/DND, simulator metadata) that can be compared to what the CUA agent perceived.

Telemetry is **environment-owned** — hooks live in `UseComputerEnvironment`, not in persona agents.

## Output layout

After a trial, Harbor collects artifacts declared in `task.toml`. System telemetry lands at:

| Location | Contents |
|----------|----------|
| Sandbox | `/tmp/personabench-telemetry/system_trace.json` |
| Host | `jobs/<job>/<trial>/artifacts/tmp/personabench-telemetry/system_trace.json` |

Agent-side artifacts (separate from system telemetry):

| Host path | Contents |
|-----------|----------|
| `agent/trajectory.json` | ATIF trajectory (persona-injected prompts, tool calls, screenshots metadata) |
| `agent/images/step_*.png` | Per-step screenshots |
| `agent/recording.mp4` | Screen recording (when `recording_enabled: true`) |

`system_trace.json` includes `links` that point at the agent trajectory when it exists on the trial host before artifact download.

## Trace schema (`schema_version: 1.0`)

```json
{
  "schema_version": "1.0",
  "platform": "macos",
  "session": {
    "trial_id": "<harbor session id>",
    "task": "personabench/application-computer-use-macos-notification-preferences",
    "started_at": "...",
    "ended_at": "...",
    "duration_sec": 312.5
  },
  "snapshots": [
    { "ts": "...", "phase": "baseline", "signals": { } },
    { "ts": "...", "phase": "step", "signals": { "step": 3, ... } },
    { "ts": "...", "phase": "final", "signals": { } }
  ],
  "artifacts": {
    "system_trace_path": "/tmp/personabench-telemetry/system_trace.json",
    "telemetry_root": "/tmp/personabench-telemetry"
  },
  "links": {
    "agent_trajectory_path": "agent/trajectory.json",
    "agent_session_id": "<uuid from trajectory>",
    "agent_step_count": 24,
    "agent_recording_path": "agent/recording.mp4"
  }
}
```

### Snapshot phases

| Phase | When |
|-------|------|
| `baseline` | Trial start, before agent runs |
| `step` | After each CUA step (`fire_in_process` → `TelemetrySession.on_step`) |
| `final` | Trial end, before sandbox teardown |

## Platform signals

### macOS

Probe runs on the remote Mac via `environment.exec` (`harbor.telemetry.macos_probe`):

- **Focus / Do Not Disturb** — `~/Library/DoNotDisturb/DB/Assertions.json`, `ModeConfigurations.json`
- **Legacy DND** — `defaults -currentHost read com.apple.notificationcenterui doNotDisturb`
- **Per-app notifications** — `com.apple.ncprefs.plist` for watched bundles (Mail, Messages, Safari, …)
- **Daemons** — `usernoted`, `NotificationCenter` process presence

### iOS Simulator

Probe runs on the **Mac host** that owns the simulator (`harbor.telemetry.ios_probe`):

- **Booted simulator** — `xcrun simctl list devices -j`, preferring `[ios]` pins in `task.toml` (`device_type`, `runtime`). Hints are normalized (`iPhone-17` ↔ `iPhone 17`, `iOS-26-4` ↔ runtime keys). If no hint match, falls back to any booted simulator (`simulator_meta.hint_fallback`).
- **Notification sections** — `VersionedSectionInfo.plist` stores per-bundle NSKeyedArchiver blobs under `sectionInfo` (parsed by `harbor.telemetry.nskeyedarchiver`). Legacy `SectionInfo.plist` is a flat bundle map. TCC is used only when BulletinBoard data is missing.
- **Privacy CLI** — `simctl privacy` supports grant/revoke/reset only (no read/status on current Xcode). When `SectionInfo.plist` is missing, probe falls back to `TCC.db` notification rows when present.

## Enable / disable

Telemetry is on by default for `use-computer` macOS and iOS:

```yaml
environment:
  type: use-computer
  kwargs:
    telemetry_enabled: true   # default
```

Tasks must list the telemetry directory in `artifacts`:

```toml
artifacts = ["/tmp/personabench-telemetry"]
```

Harbor calls `prepare_artifact_collection()` on the environment **before** downloading artifacts so `system_trace.json` is flushed while the sandbox is still up.

## Smoke jobs

| Platform | Job config |
|----------|------------|
| macOS | `configs/jobs/example-job-recipe/appSim-example-computer-use-macos-local.yaml` |
| iOS | `configs/jobs/example-job-recipe/appSim-example-computer-use-ios-local.yaml` |

Prerequisites: `USE_COMPUTER_API_KEY`, `USE_COMPUTER_RESERVATION_ID`, `ANTHROPIC_API_KEY`, and `uv sync --extra use-computer --extra computer-1`.

Oracle runs (no LLM, cheap validation of probe + artifact path):

```bash
uv run harbor run \
  -p application/tasks/example-computer-use-macos_notification-preferences \
  -a oracle -e use-computer

uv run harbor run \
  -p application/tasks/example-computer-use-ios_notification-preferences \
  -a oracle -e use-computer --ek platform=ios
```

## Demo walkthrough (macOS + iOS)

Use this script when presenting the notification-preferences computer-use demos.

### 1. macOS persona run

```bash
export USE_COMPUTER_API_KEY=...
export USE_COMPUTER_RESERVATION_ID=...
export ANTHROPIC_API_KEY=...

uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-computer-use-macos-local.yaml
```

Open the trial directory under `jobs/appSim-example-computer-use-macos-local/<trial>/`:

1. **`agent/trajectory.json`** — step 1 user message shows persona narrative + task instruction.
2. **`artifacts/tmp/personabench-macos-notification-preferences/decision.json`** — agent’s structured decision (`keep_notifications_on`, `reason`).
3. **`artifacts/tmp/personabench-telemetry/system_trace.json`** — compare `snapshots[0]` (baseline) vs `snapshots[-1]` (final) `notifications.watched_apps` for ground truth.
4. **`agent/images/`** + **`agent/recording.mp4`** — what the agent actually saw.

Talking point: the agent’s `reason` may disagree with `notifications.watched_apps` in the trace — that gap is why system telemetry matters.

### 2. iOS persona run

```bash
uv run harbor run -c configs/jobs/example-job-recipe/appSim-example-computer-use-ios-local.yaml
```

Same comparison pattern:

- `artifacts/tmp/personabench-ios-notification-preferences/decision.json`
- `artifacts/tmp/personabench-telemetry/system_trace.json` → `simulator`, `notifications.watched_apps`
- `agent/trajectory.json` + screenshots / recording

### 3. Two personas × macOS + iOS (separate job dirs)

Four job configs write to distinct `jobs/<job_name>/` trees:

| Job | Persona | Platform |
|-----|---------|----------|
| `appSim-demo-cu-macos-p0042` | `persona_0042.yaml` | macOS |
| `appSim-demo-cu-macos-p1206` | `persona_1206.yaml` | macOS |
| `appSim-demo-cu-ios-p0042` | `persona_0042.yaml` | iOS |
| `appSim-demo-cu-ios-p1206` | `persona_1206.yaml` | iOS |

```bash
export USE_COMPUTER_API_KEY=...
export USE_COMPUTER_RESERVATION_ID=...
export ANTHROPIC_API_KEY=...

./scripts/demo-cu-persona-matrix.sh          # all four
./scripts/demo-cu-persona-matrix.sh macos    # macOS pair only
./scripts/demo-cu-persona-matrix.sh ios      # iOS pair only
```

Compare `decision.json` `reason` fields across personas; `system_trace.json` ground truth should match when the agent reaches the same settings.

## Module map

| File | Role |
|------|------|
| `src/personabench/telemetry/session.py` | Lifecycle + flush + trajectory linking |
| `src/personabench/telemetry/macos_probe.py` | macOS notification / Focus probe |
| `src/personabench/telemetry/ios_probe.py` | iOS Simulator notification probe |
| `src/harbor/environments/use_computer.py` | Hooks: start, `fire_in_process`, stop, `prepare_artifact_collection` |

## Related

- [computer-use-telemetry-demo.md](computer-use-telemetry-demo.md) — live demo script (screenshots)
- [computer-use-telemetry-design.md](computer-use-telemetry-design.md) — architecture and what we added
- [docs/running.md](docs/running.md) — persona-computer-1 + API keys
- [configs/jobs/README.md](../../configs/jobs/README.md) — smoke job index
- Demo tasks: `application/tasks/example-computer-use-macos_notification-preferences`, `example-computer-use-ios_notification-preferences`
