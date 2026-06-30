import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";
import type { SurveyEvalJobView } from "./types";

export type SurveyEvalRunPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export interface StartSurveyEvalInput {
  personaId: string;
  instrumentId: string;
  personaModel?: string;
}

export function useSurveyEval() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<SurveyEvalJobView | null>(null);
  const [phase, setPhase] = useState<SurveyEvalRunPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const lastInput = useRef<StartSurveyEvalInput | null>(null);
  const startedAt = useRef<number>(0);

  const run = useCallback(async (input: StartSurveyEvalInput) => {
    lastInput.current = input;
    startedAt.current = Date.now();
    setJob(null);
    setError(null);
    setPhase("building");
    try {
      const created = await api.startSurveyEval(input);
      setJobId(created.jobId);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      setPhase("error");
    }
  }, []);

  const retry = useCallback(() => {
    if (lastInput.current) void run(lastInput.current);
  }, [run]);

  useEffect(() => {
    if (!jobId) return;
    const activeJobId = jobId;
    let cancelled = false;
    const timeoutMs = 10 * 60 * 1000;

    async function poll() {
      try {
        const view = await api.getSurveyEvalJob(activeJobId);
        if (cancelled) return;
        setJob(view);
        if (view.status === "building" || view.status === "running") {
          setPhase(view.status);
          if (Date.now() - startedAt.current > timeoutMs) {
            setPhase("timeout");
            setError("The survey run is taking longer than expected.");
            return;
          }
          window.setTimeout(poll, 1_000);
          return;
        }
        if (view.status === "done") {
          setPhase("done");
          return;
        }
        setError(view.error ?? "Survey run failed");
        setPhase("error");
      } catch (exc) {
        if (cancelled) return;
        setError(exc instanceof Error ? exc.message : String(exc));
        setPhase("error");
      }
    }

    void poll();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return {
    run,
    job,
    phase,
    error,
    timedOut: phase === "timeout",
    isRunning: phase === "building" || phase === "running",
    retry,
  };
}
