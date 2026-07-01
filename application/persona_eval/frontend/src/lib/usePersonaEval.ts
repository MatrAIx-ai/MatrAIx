import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, getPersonaEvalPersona } from "./api";
import type { PersonaEvalJobView, PersonaEvalPersona } from "./types";

export type PersonaEvalRunPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export interface StartPersonaEvalInput {
  domain?: string;
  applicationId?: string;
  applicationContext?: string;
  personaId: string;
  goalContextId?: string;
  maxTurns: number;
  engine?: string;
  personaModel?: string;
}

export function usePersonaDetail(personaId: string | null) {
  return useQuery<PersonaEvalPersona>({
    queryKey: ["persona-eval", "persona", personaId],
    queryFn: () => getPersonaEvalPersona(personaId as string),
    enabled: personaId !== null,
    staleTime: 10 * 60 * 1000,
  });
}

export function usePersonaEval() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<PersonaEvalJobView | null>(null);
  const [phase, setPhase] = useState<PersonaEvalRunPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const lastInput = useRef<StartPersonaEvalInput | null>(null);
  const startedAt = useRef<number>(0);

  const reset = useCallback(() => {
    setJobId(null);
    setJob(null);
    setPhase("idle");
    setError(null);
  }, []);

  const run = useCallback(async (input: StartPersonaEvalInput) => {
    lastInput.current = input;
    startedAt.current = Date.now();
    setJob(null);
    setError(null);
    setPhase("building");
    try {
      const created = await api.startPersonaEval(input);
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
        const view = await api.getPersonaEvalJob(activeJobId);
        if (cancelled) return;
        setJob(view);
        if (view.status === "building" || view.status === "running") {
          setPhase(view.status);
          if (Date.now() - startedAt.current > timeoutMs) {
            setPhase("timeout");
            setError("The run is taking longer than expected.");
            return;
          }
          window.setTimeout(poll, 1_000);
          return;
        }
        if (view.status === "done") {
          setPhase("done");
          return;
        }
        setError(view.error ?? "Run failed");
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
    reset,
  };
}
