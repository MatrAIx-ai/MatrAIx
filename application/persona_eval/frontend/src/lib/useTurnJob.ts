import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { api } from "./api";

export type TurnPhase = "idle" | "building" | "running" | "done" | "error" | "timeout";

export const sessionKeys = {
  list: () => ["sessions"] as const,
  detail: (id: string) => ["sessions", "detail", id] as const,
};

export function useTurnJob(sessionId: string | null, onDone?: () => void) {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [phase, setPhase] = useState<TurnPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const lastMessage = useRef<string | null>(null);
  const startedAt = useRef<number>(0);

  const reset = useCallback(() => {
    setJobId(null);
    setPhase("idle");
    setError(null);
    setPendingMessage(null);
    startedAt.current = 0;
  }, []);

  const send = useCallback(
    async (message: string) => {
      if (!sessionId || phase === "building" || phase === "running") return;
      lastMessage.current = message;
      setPendingMessage(message);
      setError(null);
      setPhase("building");
      startedAt.current = Date.now();
      try {
        const created = await api.submitTurn(sessionId, message);
        setJobId(created.jobId);
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : String(exc));
        setPhase("error");
      }
    },
    [phase, sessionId],
  );

  const retry = useCallback(() => {
    const message = lastMessage.current;
    if (message) void send(message);
  }, [send]);

  useEffect(() => {
    if (!jobId || !sessionId) return;
    const activeJobId = jobId;
    const activeSessionId = sessionId;
    let cancelled = false;
    const timeoutMs = 180_000;

    async function poll() {
      try {
        const view = await api.getTurnJob(activeJobId);
        if (cancelled) return;
        if (view.status === "building" || view.status === "running") {
          setPhase(view.status);
          if (Date.now() - startedAt.current > timeoutMs) {
            setPhase("timeout");
            setError("The turn is taking longer than expected.");
            return;
          }
          window.setTimeout(poll, 1_000);
          return;
        }
        if (view.status === "done") {
          setPhase("done");
          setPendingMessage(null);
          await queryClient.invalidateQueries({ queryKey: sessionKeys.detail(activeSessionId) });
          await queryClient.invalidateQueries({ queryKey: sessionKeys.list() });
          onDone?.();
          return;
        }
        setError(view.error ?? "Turn failed");
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
  }, [jobId, onDone, queryClient, sessionId]);

  return {
    jobId,
    phase,
    error,
    pendingMessage,
    timedOut: phase === "timeout",
    send,
    retry,
    reset,
  };
}
