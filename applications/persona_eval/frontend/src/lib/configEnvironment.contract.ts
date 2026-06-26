import type { ConfigEnvironment } from "./types";

const configEnvironmentWithPromptOwnership: ConfigEnvironment = {
  runtime: "Local direct runner",
  personaAgent: "PersonaEval simulated user",
  personaModel: "anthropic/claude-haiku-4-5",
  applicationApi: "direct application adapter",
  scorer: "PersonaEval self-report scorer",
  cache: "local service and model caches",
  ranker: "application-specific ranking / tool selection",
  resources: "adapter-specific resources",
  agent: "chatbot application adapter",
  promptOwnership: {
    personaSystemPrompt: "Persona prompt from PersonaEval",
    taskPrompt: "Application-provided chatbot simulation prompt",
  },
};

void configEnvironmentWithPromptOwnership;
