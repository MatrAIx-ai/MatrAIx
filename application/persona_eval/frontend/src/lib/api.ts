import type {
  AppWorldEvalJobView,
  AppWorldEvalTasksResponse,
  ConfigOptionsResponse,
  GoalContextsResponse,
  PersonaEvalJobView,
  PersonaEvalPersonasResponse,
  PersonaEvalResult,
  PersonaEvalRunsResponse,
  PreflightResponse,
  Session,
  SessionConfig,
  SessionSummary,
  SurveyEvalJobView,
  SurveyInstrumentsResponse,
  WebEvalJobView,
  WebEvalTasksResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data;
    const message = typeof detail === "string" ? detail : response.statusText;
    throw new ApiError(response.status, message || "Request failed", detail);
  }
  return data as T;
}

function qs(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api = {
  getPreflight: () => request<PreflightResponse>("/api/preflight"),
  getConfigOptions: () => request<ConfigOptionsResponse>("/api/config/options"),

  listSessions: () => request<SessionSummary[]>("/api/sessions"),
  getSession: (id: string) => request<Session>(`/api/sessions/${encodeURIComponent(id)}`),
  createSession: (body?: { title?: string; config?: Partial<SessionConfig> }) =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),
  patchSessionConfig: (id: string, config: Partial<SessionConfig>) =>
    request<{ session: Session; cacheInvalidated: boolean }>(
      `/api/sessions/${encodeURIComponent(id)}/config`,
      {
        method: "PATCH",
        body: JSON.stringify({ config }),
      },
    ),
  deleteSession: (id: string) =>
    request<{ deleted: string }>(`/api/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  clearSessions: () => request<{ deleted: number }>("/api/sessions", { method: "DELETE" }),
  submitTurn: (id: string, message: string) =>
    request<{ jobId: string }>(`/api/sessions/${encodeURIComponent(id)}/turns`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  getTurnJob: (id: string) =>
    request<{ jobId: string; status: string; turn?: unknown; error?: string | null }>(
      `/api/jobs/${encodeURIComponent(id)}`,
    ),

  startPersonaEval: (body: {
    domain?: string;
    applicationId?: string;
    applicationContext?: string;
    personaId: string;
    maxTurns: number;
    goalContextId?: string | null;
    engine?: string | null;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/persona-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getPersonaEvalJob: (id: string) =>
    request<PersonaEvalJobView>(`/api/persona-eval/jobs/${encodeURIComponent(id)}`),
  listPersonaEvalRuns: () => request<PersonaEvalRunsResponse>("/api/persona-eval/runs"),
  getPersonaEvalRun: (id: string) =>
    request<PersonaEvalResult>(`/api/persona-eval/runs/${encodeURIComponent(id)}`),

  startSurveyEval: (body: {
    personaId: string;
    instrumentId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/survey-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSurveyEvalJob: (id: string) =>
    request<SurveyEvalJobView>(`/api/survey-eval/jobs/${encodeURIComponent(id)}`),

  startWebEval: (body: {
    personaId: string;
    taskId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/web-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getWebEvalJob: (id: string) =>
    request<WebEvalJobView>(`/api/web-eval/jobs/${encodeURIComponent(id)}`),

  startAppWorldEval: (body: {
    personaId: string;
    taskId: string;
    personaModel?: string | null;
  }) =>
    request<{ jobId: string }>("/api/appworld-eval", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getAppWorldEvalJob: (id: string) =>
    request<AppWorldEvalJobView>(`/api/appworld-eval/jobs/${encodeURIComponent(id)}`),
};

export function sessionExportUrl(id: string): string {
  return `/api/sessions/${encodeURIComponent(id)}/export`;
}

export function listPersonaEvalPersonas(input?: {
  q?: string;
  limit?: number;
  domain?: string | null;
}): Promise<PersonaEvalPersonasResponse> {
  return request<PersonaEvalPersonasResponse>(
    `/api/persona-eval/personas${qs({
      q: input?.q,
      limit: input?.limit,
      domain: input?.domain,
    })}`,
  );
}

export function getPersonaEvalPersona(id: string): Promise<PersonaEvalPersonasResponse["personas"][number]> {
  return request<PersonaEvalPersonasResponse["personas"][number]>(
    `/api/persona-eval/personas/${encodeURIComponent(id)}`,
  );
}

export function listGoalContexts(): Promise<GoalContextsResponse> {
  return request<GoalContextsResponse>("/api/persona-eval/goal-contexts");
}

export function listSurveyInstruments(): Promise<SurveyInstrumentsResponse> {
  return request<SurveyInstrumentsResponse>("/api/survey-eval/instruments");
}

export function listWebEvalTasks(): Promise<WebEvalTasksResponse> {
  return request<WebEvalTasksResponse>("/api/web-eval/tasks");
}

export function listAppWorldEvalTasks(): Promise<AppWorldEvalTasksResponse> {
  return request<AppWorldEvalTasksResponse>("/api/appworld-eval/tasks");
}
