import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listAppWorldEvalTasks } from "@/lib/api";
import { useAppWorldEval, type AppWorldEvalRunPhase } from "@/lib/useAppWorldEval";
import { usePersonaDetail } from "@/lib/usePersonaEval";
import type {
  AppWorldEvalTask,
  AppWorldEvalTasksResponse,
  AppWorldTraceEvent,
  ConfigOptionsResponse,
  PersonaEvalPersona,
  PersonaModel,
} from "@/lib/types";
import { PersonaCatalog } from "./PersonaCatalog";
import { PersonaDrawer } from "./PersonaDrawer";
import { PromptPanel } from "./PromptPanel";
import { TaskTypeSwitch, type PersonaEvalTaskType } from "./TaskTypeSwitch";
import {
  FOCUS_RING,
  Sym,
  parseDemographics,
  parseDemographicsFromBlurb,
  personaCodename,
  personaDescriptiveTitle,
} from "./cockpitShared";

export interface AppWorldEvalCockpitProps {
  options: ConfigOptionsResponse | null;
  taskType: PersonaEvalTaskType;
  onTaskTypeChange: (value: PersonaEvalTaskType) => void;
  onFooterContextChange?: (context: string) => void;
}

interface SelectOption {
  value: string;
  label: string;
}

function optionsFor(options: ConfigOptionsResponse | null, key: string): SelectOption[] {
  const knob = options?.knobs.find((item) => item.key === key);
  return knob ? knob.options.map((item) => ({ value: item.value, label: item.label })) : [];
}

function statusLine(phase: AppWorldEvalRunPhase, jobPhase: string | null | undefined): string | null {
  if (phase === "building") return "Starting the AppWorld agent…";
  if (phase !== "running") return null;
  const raw = (jobPhase ?? "").toLowerCase();
  if (raw.includes("collect")) return "Saving the AppWorld result and trace…";
  if (raw.includes("appworld")) return "The hosted agent is calling AppWorld APIs…";
  return "Running the AppWorld task…";
}

function actionLabel(event: AppWorldTraceEvent): string {
  const action = event.actions[0];
  if (!action) return "step";
  const args = action.arguments ?? {};
  const app = typeof args.app === "string" ? args.app : null;
  const method = typeof args.method === "string" ? args.method : null;
  if (app && method) return `${app}.${method}`;
  return action.name.replace(/_/g, " ");
}

export function AppWorldEvalCockpit({
  options,
  taskType,
  onTaskTypeChange,
  onFooterContextChange,
}: AppWorldEvalCockpitProps) {
  const { run, job, phase, isRunning, error, timedOut, retry } = useAppWorldEval();
  const [persona, setPersona] = useState<PersonaEvalPersona | null>(null);
  const [taskId, setTaskId] = useState("appworld-demo-personal-admin");
  const [personaModel, setPersonaModel] = useState<string>(
    options?.environment.personaModel ?? "anthropic/claude-haiku-4-5",
  );
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [exportSnapshot, setExportSnapshot] = useState<{
    persona: { id: string; name: string; source: string } | null;
    task: AppWorldEvalTask | null;
    personaModel: string;
  } | null>(null);

  const adoptedDefaults = useRef(false);
  useEffect(() => {
    if (adoptedDefaults.current || !options) return;
    adoptedDefaults.current = true;
    setPersonaModel(options.environment.personaModel ?? "anthropic/claude-haiku-4-5");
  }, [options]);

  const tasksQuery = useQuery<AppWorldEvalTasksResponse>({
    queryKey: ["appworld-eval-tasks"],
    queryFn: listAppWorldEvalTasks,
    staleTime: 10 * 60 * 1000,
  });
  const tasks = useMemo(() => tasksQuery.data?.tasks ?? [], [tasksQuery.data]);
  const task = tasks.find((item) => item.id === taskId) ?? tasks[0] ?? null;
  const personaModelOptions = optionsFor(options, "personaModel");
  const detail = usePersonaDetail(persona?.id ?? null);
  const personaContext = detail.data?.context ?? persona?.context ?? null;
  const demographics = useMemo(() => {
    if (personaContext) {
      const parsed = parseDemographics(personaContext);
      if (parsed.length > 0) return parsed;
    }
    return parseDemographicsFromBlurb(persona?.blurb);
  }, [personaContext, persona?.blurb]);

  useEffect(() => {
    if (!tasks.some((item) => item.id === taskId) && tasks[0]) {
      setTaskId(tasks[0].id);
    }
  }, [taskId, tasks]);

  useEffect(() => {
    onFooterContextChange?.(`appworld · ${task?.appName ?? "AppWorld"} · ${task?.title ?? "task"}`);
  }, [onFooterContextChange, task]);

  const handleRun = useCallback(() => {
    if (!persona || !task || isRunning) return;
    setExportSnapshot(null);
    run({
      personaId: persona.id,
      taskId: task.id,
      personaModel: personaModel as PersonaModel,
    });
  }, [persona, task, isRunning, run, personaModel]);

  const handleRetry = useCallback(() => {
    if (timedOut || phase === "error") retry();
    else handleRun();
  }, [handleRun, phase, retry, timedOut]);

  const handleExport = useCallback(() => {
    if (!exportSnapshot || !job?.appworldResult) return;
    const payload = {
      applicationType: "appworld",
      config: exportSnapshot,
      appworldResult: job.appworldResult,
      trace: job.trace,
      prompts: job.prompts,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `appworld-eval-${exportSnapshot.persona?.id ?? "run"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [exportSnapshot, job]);

  const result = job?.appworldResult ?? null;
  const trace = job?.trace ?? null;
  const prompts = job?.prompts ?? null;
  const message = statusLine(phase, job?.phase);
  const canRun = Boolean(persona && task) && !isRunning;

  useEffect(() => {
    if (phase === "done") {
      setExportSnapshot(
        (prev) =>
          prev ?? {
            persona: persona ? { id: persona.id, name: persona.name, source: persona.source } : null,
            task,
            personaModel,
          },
      );
    }
  }, [phase, persona, personaModel, task]);

  return (
    <div className="relative z-0 flex min-h-0 flex-1 bg-surface-dim">
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <PersonaCatalog selectedId={persona?.id ?? null} onSelect={setPersona} />

        <main className="custom-scrollbar min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1180px] px-6 py-7">
            <div className="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
              <div>
                <div className="hud mb-2 text-[10px] text-primary">PersonaEval · Cockpit</div>
                <h1 className="font-display text-[26px] font-bold tracking-tight text-text-main">
                  Configure a simulation
                </h1>
                <p className="mt-1 text-[13px] text-text-variant">
                  Pick a persona and an AppWorld task. BenchFlow hosts the agent and returns the API trajectory.
                </p>
              </div>
              <TaskTypeSwitch value={taskType} onChange={onTaskTypeChange} disabled={isRunning} />
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
              <section className="space-y-4">
                <RunPanel
                  task={task}
                  tasks={tasks}
                  tasksLoading={tasksQuery.isLoading}
                  tasksError={tasksQuery.isError}
                  persona={persona}
                  personaContext={personaContext}
                  demographics={demographics}
                  personaModel={personaModel}
                  personaModelOptions={personaModelOptions}
                  isRunning={isRunning}
                  canRun={canRun}
                  phase={phase}
                  status={message}
                  onTaskChange={setTaskId}
                  onPersonaModelChange={setPersonaModel}
                  onRun={handleRun}
                  onRetry={handleRetry}
                  onOpenPersona={() => setDrawerOpen(true)}
                  onExport={handleExport}
                  hasResult={Boolean(result)}
                />

                {(phase !== "idle" || result || error) && (
                  <ResultPanel
                    phase={phase}
                    error={error}
                    result={result}
                    trace={trace}
                    onRetry={handleRetry}
                  />
                )}
              </section>

              <aside className="space-y-4">
                <TracePanel trace={trace} phase={phase} />
                <PromptPanel prompts={prompts} />
              </aside>
            </div>
          </div>
        </main>
      </div>

      <PersonaDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        persona={persona}
        context={personaContext}
      />
    </div>
  );
}

function RunPanel({
  task,
  tasks,
  tasksLoading,
  tasksError,
  persona,
  personaContext,
  demographics,
  personaModel,
  personaModelOptions,
  isRunning,
  canRun,
  phase,
  status,
  onTaskChange,
  onPersonaModelChange,
  onRun,
  onRetry,
  onOpenPersona,
  onExport,
  hasResult,
}: {
  task: AppWorldEvalTask | null;
  tasks: AppWorldEvalTask[];
  tasksLoading: boolean;
  tasksError: boolean;
  persona: PersonaEvalPersona | null;
  personaContext: string | null;
  demographics: ReturnType<typeof parseDemographics>;
  personaModel: string;
  personaModelOptions: SelectOption[];
  isRunning: boolean;
  canRun: boolean;
  phase: AppWorldEvalRunPhase;
  status: string | null;
  onTaskChange: (taskId: string) => void;
  onPersonaModelChange: (model: string) => void;
  onRun: () => void;
  onRetry: () => void;
  onOpenPersona: () => void;
  onExport: () => void;
  hasResult: boolean;
}) {
  const title = persona
    ? personaDescriptiveTitle(personaContext, persona.blurb, persona.source)
    : "No persona selected";
  const codename = persona ? personaCodename(persona.name, persona.id) : null;

  return (
    <section className="rounded-md border border-outline bg-surface-lowest p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="hud mb-1.5 text-[9px] text-primary">AppWorld run</div>
          <h2 className="font-display text-[18px] font-bold text-text-main">Agent + prompt</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onExport}
            disabled={!hasResult}
            className={`inline-flex items-center gap-1.5 rounded-md border border-outline bg-surface px-3 py-2 text-[12px] font-medium text-text-variant transition hover:text-text-main disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
          >
            <Sym name="download" size={15} />
            Export
          </button>
          <button
            type="button"
            onClick={phase === "error" || phase === "timeout" ? onRetry : onRun}
            disabled={!canRun && !(phase === "error" || phase === "timeout")}
            className={`inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-[12px] font-semibold text-on-primary transition hover:bg-primary-dim disabled:cursor-not-allowed disabled:opacity-50 ${FOCUS_RING}`}
          >
            <Sym name={isRunning ? "autorenew" : phase === "error" || phase === "timeout" ? "refresh" : "play_arrow"} size={16} fill={1} className={isRunning ? "animate-rb-spin" : ""} />
            {isRunning ? "Running" : phase === "error" || phase === "timeout" ? "Retry" : "Run eval"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="hud mb-1.5 block text-[9px] text-text-dim">Task</span>
          <select
            value={task?.id ?? ""}
            disabled={isRunning || tasksLoading || tasksError}
            onChange={(e) => onTaskChange(e.target.value)}
            className={`h-10 w-full rounded-md border border-outline bg-field px-3 text-[13px] text-text-main ${FOCUS_RING}`}
          >
            {tasks.length === 0 && <option value="">{tasksLoading ? "Loading tasks..." : "No tasks"}</option>}
            {tasks.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="hud mb-1.5 block text-[9px] text-text-dim">Persona model</span>
          <select
            value={personaModel}
            disabled={isRunning}
            onChange={(e) => onPersonaModelChange(e.target.value)}
            className={`h-10 w-full rounded-md border border-outline bg-field px-3 text-[13px] text-text-main ${FOCUS_RING}`}
          >
            {personaModelOptions.length === 0 ? (
              <option value={personaModel}>{personaModel}</option>
            ) : (
              personaModelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))
            )}
          </select>
        </label>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-outline bg-surface p-4">
          <div className="hud mb-2 text-[9px] text-text-dim">Target persona</div>
          {persona ? (
            <>
              <div className="flex items-start gap-3">
                <div className="grid h-10 w-10 flex-none place-items-center rounded-full border border-primary/20 bg-primary/10">
                  <Sym name="face" fill={1} size={24} className="text-primary" />
                </div>
                <div className="min-w-0">
                  <div className="line-clamp-2 font-semibold text-text-main">{title}</div>
                  <div className="mt-0.5 truncate font-mono text-[11px] text-text-dim">{codename}</div>
                </div>
              </div>
              {demographics.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {demographics.map((item) => (
                    <span key={item.key} title={item.full} className="rounded border border-outline bg-surface-high px-2 py-0.5 text-[11px] text-text-variant">
                      {item.text}
                    </span>
                  ))}
                </div>
              )}
              <button
                type="button"
                onClick={onOpenPersona}
                className={`mt-3 inline-flex items-center gap-1.5 text-[12px] font-medium text-primary hover:text-primary-dim ${FOCUS_RING}`}
              >
                <Sym name="open_in_new" size={14} />
                Full persona
              </button>
            </>
          ) : (
            <p className="text-[13px] leading-relaxed text-text-variant">Choose a persona from the catalog.</p>
          )}
        </div>

        <div className="rounded-md border border-outline bg-surface p-4">
          <div className="hud mb-2 text-[9px] text-text-dim">Task contract</div>
          <h3 className="font-semibold text-text-main">{task?.appName ?? "AppWorld"}</h3>
          <p className="mt-2 text-[13px] leading-relaxed text-text-variant">
            {task?.description ?? "The AppWorld task metadata is loading."}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="rounded border border-outline bg-surface-high px-2 py-0.5 font-mono text-[10px] text-text-dim">
              {task?.outputArtifact ?? "appworld_result.json"}
            </span>
            <span className="rounded border border-outline bg-surface-high px-2 py-0.5 font-mono text-[10px] text-text-dim">
              trace.json
            </span>
          </div>
        </div>
      </div>

      {status && (
        <div className="mt-4 flex items-center gap-2 rounded-md border border-primary/20 bg-primary/10 px-3 py-2 text-[12px] text-primary">
          <Sym name="sync" size={15} className="animate-rb-spin" />
          {status}
        </div>
      )}
    </section>
  );
}

function ResultPanel({
  phase,
  error,
  result,
  trace,
  onRetry,
}: {
  phase: AppWorldEvalRunPhase;
  error: string | null;
  result: { success: boolean; score: number; outcome: string; reason: string } | null;
  trace: { events: AppWorldTraceEvent[] } | null | undefined;
  onRetry: () => void;
}) {
  if (phase === "error" || phase === "timeout") {
    return (
      <section className="rounded-md border border-danger/30 bg-danger/10 p-5">
        <div className="flex items-start gap-3">
          <Sym name="error" fill={1} size={20} className="mt-0.5 text-danger" />
          <div>
            <h2 className="font-semibold text-text-main">AppWorld run failed</h2>
            <p className="mt-1 text-[13px] text-text-variant">{error ?? "The run did not finish."}</p>
            <button
              type="button"
              onClick={onRetry}
              className={`mt-3 inline-flex items-center gap-1.5 rounded-md border border-danger/40 px-3 py-1.5 text-[12px] font-medium text-danger hover:bg-danger/10 ${FOCUS_RING}`}
            >
              <Sym name="refresh" size={15} />
              Try again
            </button>
          </div>
        </div>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="rounded-md border border-outline bg-surface-lowest p-5">
        <div className="hud text-[9px] text-text-dim">Result</div>
        <p className="mt-2 text-[13px] text-text-variant">Waiting for the AppWorld result artifact.</p>
      </section>
    );
  }

  const score = Math.round(result.score * 100);
  return (
    <section className="rounded-md border border-outline bg-surface-lowest p-5">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-md border border-outline bg-surface p-4">
          <div className="hud text-[9px] text-text-dim">Success</div>
          <div className={`mt-2 flex items-center gap-2 text-[20px] font-bold ${result.success ? "text-secondary" : "text-danger"}`}>
            <Sym name={result.success ? "check_circle" : "cancel"} fill={1} size={22} />
            {result.success ? "Yes" : "No"}
          </div>
        </div>
        <div className="rounded-md border border-outline bg-surface p-4">
          <div className="hud text-[9px] text-text-dim">Score</div>
          <div className="mt-2 font-display text-[28px] font-bold text-text-main">{score}%</div>
        </div>
        <div className="rounded-md border border-outline bg-surface p-4">
          <div className="hud text-[9px] text-text-dim">Trace steps</div>
          <div className="mt-2 font-display text-[28px] font-bold text-text-main">{trace?.events.length ?? 0}</div>
        </div>
      </div>
      <div className="mt-4 rounded-md border border-outline bg-surface p-4">
        <div className="hud text-[9px] text-text-dim">Outcome</div>
        <p className="mt-2 text-[13px] leading-relaxed text-text-main">{result.outcome}</p>
        <p className="mt-2 text-[12px] leading-relaxed text-text-variant">{result.reason}</p>
      </div>
    </section>
  );
}

function TracePanel({
  trace,
  phase,
}: {
  trace: { events: AppWorldTraceEvent[] } | null | undefined;
  phase: AppWorldEvalRunPhase;
}) {
  const events = trace?.events ?? [];
  return (
    <section className="rounded-md border border-outline bg-surface-lowest">
      <div className="border-b border-outline px-4 py-3">
        <div className="hud text-[9px] text-primary">Trajectory</div>
        <h2 className="mt-1 font-semibold text-text-main">AppWorld API calls</h2>
      </div>
      <div className="max-h-[360px] overflow-y-auto p-4 custom-scrollbar">
        {events.length === 0 ? (
          <div className="rounded-md border border-dashed border-outline-dim bg-surface-low px-4 py-8 text-center">
            <Sym name={phase === "running" ? "sync" : "route"} size={24} className={phase === "running" ? "animate-rb-spin text-primary" : "text-text-dim"} />
            <p className="mt-2 text-[13px] text-text-variant">
              {phase === "running" || phase === "building" ? "Waiting for trajectory events." : "Run AppWorld to see the API trajectory."}
            </p>
          </div>
        ) : (
          <ol className="space-y-3">
            {events.map((event, index) => (
              <li key={`${event.step}-${index}`} className="rounded-md border border-outline bg-surface p-3">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="hud text-[9px] text-text-dim">Step {event.step}</span>
                  <span className="rounded bg-surface-high px-2 py-0.5 font-mono text-[10px] text-primary">
                    {actionLabel(event)}
                  </span>
                </div>
                <p className="text-[13px] leading-relaxed text-text-main">{event.message ?? "AppWorld API step"}</p>
                {event.actions.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {event.actions.map((action, actionIndex) => (
                      <span key={`${action.name}-${actionIndex}`} className="rounded border border-outline bg-field px-2 py-1 font-mono text-[10px] text-text-variant">
                        {action.name}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}

export default AppWorldEvalCockpit;
