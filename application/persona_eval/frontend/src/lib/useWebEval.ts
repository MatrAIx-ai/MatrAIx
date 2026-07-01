import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";
import type { WebEvalJobView } from "./types";

export type WebEvalRunPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export interface StartWebEvalInput {
  personaId: string;
  taskId: string;
  personaModel?: string;
}

export function useWebEval() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<WebEvalJobView | null>(null);
  const [phase, setPhase] = useState<WebEvalRunPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const lastInput = useRef<StartWebEvalInput | null>(null);
  const startedAt = useRef<number>(0);

  const run = useCallback(async (input: StartWebEvalInput) => {
    lastInput.current = input;
    startedAt.current = Date.now();
    setJob(null);
    setError(null);
    setPhase("building");
    try {
      const created = await api.startWebEval(input);
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
        const view = await api.getWebEvalJob(activeJobId);
        if (cancelled) return;
        setJob(view);
        if (view.status === "building" || view.status === "running") {
          setPhase(view.status);
          if (Date.now() - startedAt.current > timeoutMs) {
            setPhase("timeout");
            setError("The web run is taking longer than expected.");
            return;
          }
          window.setTimeout(poll, 1_000);
          return;
        }
        if (view.status === "done") {
          setPhase("done");
          return;
        }
        setError(view.error ?? "Web run failed");
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
