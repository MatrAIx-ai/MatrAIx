import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getSurveyEvalJob, startSurveyEval } from "./api";
import type { JobStatus, PersonaModel, SurveyEvalJobView } from "./types";

const POLL_INTERVAL_MS = 1200;
const MAX_POLL_DURATION_MS = 10 * 60_000;

export interface RunSurveyEvalInput {
  personaId: string;
  instrumentId?: string;
  personaModel?: PersonaModel;
}

export type SurveyEvalRunPhase = JobStatus | "idle" | "timeout";

export interface UseSurveyEvalResult {
  run: (input: RunSurveyEvalInput) => void;
  job: SurveyEvalJobView | null;
  phase: SurveyEvalRunPhase;
  isRunning: boolean;
  error: string | null;
  timedOut: boolean;
  retry: () => void;
  reset: () => void;
}

export function useSurveyEval(): UseSurveyEvalResult {
  const [jobId, setJobId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [pollStartedAt, setPollStartedAt] = useState<number | null>(null);
  const lastInputRef = useRef<RunSurveyEvalInput | null>(null);

  const mutation = useMutation({
    mutationFn: (input: RunSurveyEvalInput) => startSurveyEval(input),
    onMutate: (input: RunSurveyEvalInput) => {
      setStartError(null);
      setTimedOut(false);
      lastInputRef.current = input;
    },
    onSuccess: (res) => {
      setJobId(res.jobId);
      setPollStartedAt(Date.now());
    },
    onError: (err: unknown) => {
      setStartError(err instanceof Error ? err.message : "Failed to start survey run");
    },
  });

  const query = useQuery<SurveyEvalJobView>({
    queryKey: ["survey-eval", jobId],
    queryFn: () => getSurveyEvalJob(jobId as string),
    enabled: jobId !== null && !timedOut,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "done" || status === "error") return false;
      if (pollStartedAt !== null && Date.now() - pollStartedAt > MAX_POLL_DURATION_MS) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
    refetchOnWindowFocus: false,
    gcTime: 0,
  });

  const job = jobId !== null ? query.data ?? null : null;
  const jobStatus = job?.status;

  useEffect(() => {
    if (jobId === null || pollStartedAt === null || timedOut) return;
    if (jobStatus === "done" || jobStatus === "error") return;
    const remaining = MAX_POLL_DURATION_MS - (Date.now() - pollStartedAt);
    const timer = setTimeout(() => setTimedOut(true), Math.max(0, remaining));
    return () => clearTimeout(timer);
  }, [jobId, pollStartedAt, timedOut, jobStatus]);

  useEffect(() => {
    if (jobStatus === "done" || jobStatus === "error") setPollStartedAt(null);
  }, [jobStatus]);

  let phase: SurveyEvalRunPhase = "idle";
  if (timedOut) {
    phase = "timeout";
  } else if (mutation.isPending) {
    phase = "building";
  } else if (job) {
    phase = job.status;
  }

  const isRunning = phase === "building" || phase === "running";
  const error =
    startError ??
    job?.error ??
    (timedOut ? "The survey run is taking too long. The backend may be stuck." : null);

  const run = useCallback(
    (input: RunSurveyEvalInput) => {
      setStartError(null);
      setTimedOut(false);
      setPollStartedAt(null);
      setJobId(null);
      mutation.mutate(input);
    },
    [mutation],
  );

  const retry = useCallback(() => {
    const input = lastInputRef.current;
    if (!input || isRunning) return;
    setStartError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    setJobId(null);
    mutation.mutate(input);
  }, [isRunning, mutation]);

  const reset = useCallback(() => {
    setJobId(null);
    setStartError(null);
    setTimedOut(false);
    setPollStartedAt(null);
    lastInputRef.current = null;
  }, []);

  return useMemo(
    () => ({ run, job, phase, isRunning, error, timedOut, retry, reset }),
    [run, job, phase, isRunning, error, timedOut, retry, reset],
  );
}
