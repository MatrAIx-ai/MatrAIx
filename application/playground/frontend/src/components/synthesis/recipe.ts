/**
 * The "recipe": accumulated adjustments (pins, prior edits, category scales,
 * edge factors) that compile into one /api/synthesis/sample request.
 */
import type { SynthesisSampleRequest } from "@/lib/types";

export type RecipeEntry =
  | { kind: "pin"; nodeId: string; label: string; value: string }
  | { kind: "prior"; nodeId: string; label: string; values: string[]; weights: number[] }
  | { kind: "category"; category: string; factor: number }
  | {
      kind: "edge";
      source: string;
      target: string;
      sourceLabel: string;
      targetLabel: string;
      factor: number;
    };

export interface SamplingControls {
  n: number;
  seed: number;
  gammaScale: number;
  compareBaseline: boolean;
}

export const DEFAULT_CONTROLS: SamplingControls = {
  n: 50,
  seed: 42,
  gammaScale: 1,
  compareBaseline: true,
};

export const MAX_SAFE_SEED = 9_007_199_254_740_991;

export function validateSamplingControls(controls: SamplingControls): string | null {
  if (!Number.isInteger(controls.n) || controls.n < 1 || controls.n > 200) {
    return "Personas must be an integer between 1 and 200.";
  }
  if (
    !Number.isSafeInteger(controls.seed) ||
    controls.seed < 0 ||
    controls.seed > MAX_SAFE_SEED
  ) {
    return `Seed must be a safe integer between 0 and ${MAX_SAFE_SEED}.`;
  }
  if (!Number.isFinite(controls.gammaScale) || controls.gammaScale < 0) {
    return "Gamma must be a finite number greater than or equal to 0.";
  }
  return null;
}

export function recipeKey(entry: RecipeEntry): string {
  switch (entry.kind) {
    case "pin":
      return `pin:${entry.nodeId}`;
    case "prior":
      return `prior:${entry.nodeId}`;
    case "category":
      return `category:${entry.category}`;
    case "edge":
      return `edge:${entry.source}->${entry.target}`;
  }
}

/** Insert or replace the entry occupying the same recipe key. */
export function upsertEntry(recipe: RecipeEntry[], entry: RecipeEntry): RecipeEntry[] {
  const key = recipeKey(entry);
  const index = recipe.findIndex((existing) => recipeKey(existing) === key);
  if (index === -1) return [...recipe, entry];
  const next = [...recipe];
  next[index] = entry;
  return next;
}

export function buildSampleRequest(
  recipe: RecipeEntry[],
  controls: SamplingControls,
): SynthesisSampleRequest {
  const request: SynthesisSampleRequest = {
    n: controls.n,
    seed: controls.seed,
    gammaScale: controls.gammaScale,
    pins: {},
    overrides: { edgeWeights: {}, nodePriors: {}, categoryScales: {} },
    compareBaseline: controls.compareBaseline,
  };
  for (const entry of recipe) {
    if (entry.kind === "pin") request.pins[entry.nodeId] = entry.value;
    else if (entry.kind === "prior") request.overrides.nodePriors[entry.nodeId] = entry.weights;
    else if (entry.kind === "category") request.overrides.categoryScales[entry.category] = entry.factor;
    else request.overrides.edgeWeights[`${entry.source}->${entry.target}`] = entry.factor;
  }
  return request;
}

/** Map a 422 payload key (e.g. "pins.age_bracket") back to a recipe key. */
export function recipeKeyForErrorKey(errorKey: string): string | null {
  const pin = /^pins\.(.+)$/.exec(errorKey);
  if (pin) return `pin:${pin[1]}`;
  const prior = /^overrides\.nodePriors\.(.+)$/.exec(errorKey);
  if (prior) return `prior:${prior[1]}`;
  const category = /^overrides\.categoryScales\.(.+)$/.exec(errorKey);
  if (category) return `category:${category[1]}`;
  const edge = /^overrides\.edgeWeights\.(.+)$/.exec(errorKey);
  if (edge) return `edge:${edge[1]}`;
  return null;
}
