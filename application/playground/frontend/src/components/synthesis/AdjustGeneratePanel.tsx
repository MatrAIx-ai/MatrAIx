/**
 * Panel 4 — "Adjust & Generate": editable recipe entries (pins, prior edits,
 * category scales, edge factors), sampling controls, and the Generate CTA.
 * Entries are appended from the graph/detail panels; editing happens here.
 */
import type { ReactNode } from "react";

import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";
import type { RecipeEntry, SamplingControls } from "./recipe";
import { recipeKey, validateSamplingControls } from "./recipe";

const NUMBER_FIELD = `h-8 w-20 rounded border border-outline bg-field px-2 text-xs text-text-main ${FOCUS_RING}`;

function FactorSlider({
  value,
  onChange,
  label,
}: {
  value: number;
  onChange: (next: number) => void;
  label: string;
}) {
  return (
    <span className="flex min-w-0 flex-1 items-center gap-2">
      <input
        type="range"
        min={0}
        max={3}
        step={0.1}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
        className={`min-w-0 flex-1 accent-[rgb(var(--primary))] ${FOCUS_RING}`}
      />
      <span className="w-10 flex-none text-right font-mono text-[11px] text-text-variant">
        {value.toFixed(1)}×
      </span>
    </span>
  );
}

function EntryShell({
  invalid,
  helper,
  onRemove,
  removeLabel,
  children,
}: {
  invalid: boolean;
  helper: boolean;
  onRemove: () => void;
  removeLabel: string;
  children: ReactNode;
}) {
  return (
    <li
      data-testid="synthesis-recipe-entry"
      data-invalid={invalid ? "true" : "false"}
      className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 ${
        invalid ? "border-danger/70 bg-danger/5" : "border-outline-dim bg-surface-low/50"
      }`}
    >
      <div className="min-w-0 flex-1">{children}</div>
      {helper ? (
        <span className="hud flex-none text-warn" title="Pinned node is a latent helper (emit: false)">
          helper
        </span>
      ) : null}
      <button
        type="button"
        aria-label={removeLabel}
        onClick={onRemove}
        className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
      >
        <Sym name="close" size={14} />
      </button>
    </li>
  );
}

export function AdjustGeneratePanel({
  recipe,
  onUpsert,
  onRemove,
  controls,
  onControlsChange,
  onGenerate,
  generating,
  error,
  helperPins,
}: {
  recipe: RecipeEntry[];
  onUpsert: (entry: RecipeEntry) => void;
  onRemove: (key: string) => void;
  controls: SamplingControls;
  onControlsChange: (controls: SamplingControls) => void;
  onGenerate: () => void;
  generating: boolean;
  error: { message: string; key: string | null } | null;
  helperPins: string[];
}) {
  const invalidKey = error?.key ?? null;
  const controlsError = validateSamplingControls(controls);
  return (
    <div className="custom-scrollbar flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="hud mb-1 text-text-dim">Recipe</div>
        {recipe.length === 0 ? (
          <p className="text-xs leading-relaxed text-text-dim">
            No adjustments yet — pin values, edit priors, or scale influence from the
            graph panels above. Generate works without a recipe (pure baseline).
          </p>
        ) : (
          <ul className="space-y-1.5">
            {recipe.map((entry) => {
              const key = recipeKey(entry);
              const invalid = invalidKey === key;
              if (entry.kind === "pin") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={helperPins.includes(entry.nodeId)}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove pin on ${entry.label}`}
                  >
                    <span className="flex items-baseline gap-1.5 text-xs">
                      <Sym name="push_pin" size={13} className="translate-y-0.5 text-primary" />
                      <span className="truncate text-text-main">{entry.label}</span>
                      <span className="text-text-dim">=</span>
                      <span className="truncate font-mono text-[11px] text-text-variant">
                        {entry.value}
                      </span>
                    </span>
                  </EntryShell>
                );
              }
              if (entry.kind === "category") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={false}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove influence scale for ${entry.category}`}
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <span className="w-40 flex-none truncate text-text-main" title={entry.category}>
                        {entry.category}
                      </span>
                      <FactorSlider
                        value={entry.factor}
                        label={`Influence of ${entry.category}`}
                        onChange={(factor) => onUpsert({ ...entry, factor })}
                      />
                    </span>
                  </EntryShell>
                );
              }
              if (entry.kind === "edge") {
                return (
                  <EntryShell
                    key={key}
                    invalid={invalid}
                    helper={false}
                    onRemove={() => onRemove(key)}
                    removeLabel={`Remove weight factor for ${entry.sourceLabel} to ${entry.targetLabel}`}
                  >
                    <span className="flex items-center gap-2 text-xs">
                      <span
                        className="w-40 flex-none truncate text-text-main"
                        title={`${entry.sourceLabel} → ${entry.targetLabel}`}
                      >
                        {entry.sourceLabel} → {entry.targetLabel}
                      </span>
                      <FactorSlider
                        value={entry.factor}
                        label={`Weight factor for ${entry.sourceLabel} to ${entry.targetLabel}`}
                        onChange={(factor) => onUpsert({ ...entry, factor })}
                      />
                    </span>
                  </EntryShell>
                );
              }
              const total = entry.weights.reduce((sum, w) => sum + w, 0);
              return (
                <EntryShell
                  key={key}
                  invalid={invalid}
                  helper={false}
                  onRemove={() => onRemove(key)}
                  removeLabel={`Remove prior adjustment for ${entry.label}`}
                >
                  <div className="text-xs">
                    <div className="mb-1 flex items-baseline gap-1.5">
                      <Sym name="tune" size={13} className="translate-y-0.5 text-primary" />
                      <span className="truncate text-text-main">{entry.label}</span>
                      <span className="text-[10px] text-text-dim">prior</span>
                    </div>
                    <ul className="max-h-36 space-y-1 overflow-y-auto pr-1">
                      {entry.values.map((value, index) => {
                        const weight = entry.weights[index] ?? 0;
                        const share = total > 0 ? weight / total : 0;
                        return (
                          <li key={`${index}:${value}`} className="flex items-center gap-2">
                            <span
                              className="w-24 flex-none truncate text-[11px] text-text-variant"
                              title={value}
                            >
                              {value}
                            </span>
                            <input
                              type="number"
                              min={0}
                              step={0.1}
                              value={weight}
                              aria-label={`Prior weight for ${entry.label} = ${value}`}
                              onChange={(event) => {
                                const nextWeight = Number(event.target.value);
                                const weights = [...entry.weights];
                                weights[index] = Number.isFinite(nextWeight)
                                  ? Math.max(0, nextWeight)
                                  : 0;
                                onUpsert({ ...entry, weights });
                              }}
                              className={`h-7 w-16 flex-none rounded border border-outline bg-field px-1.5 text-[11px] text-text-main ${FOCUS_RING}`}
                            />
                            <span className="h-1.5 min-w-0 flex-1 rounded-sm bg-surface-high" aria-hidden="true">
                              <span
                                className="block h-full rounded-sm"
                                style={{
                                  width: `${Math.round(share * 100)}%`,
                                  background: "rgb(var(--primary) / 0.55)",
                                }}
                              />
                            </span>
                            <span className="w-10 flex-none text-right font-mono text-[10px] text-text-dim">
                              {(share * 100).toFixed(0)}%
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </EntryShell>
              );
            })}
          </ul>
        )}
      </div>

      <div className="border-t border-outline-dim pt-3">
        <div className="hud mb-2 text-text-dim">Sampling</div>
        <div className="flex flex-wrap items-end gap-3">
          {(
            [
              ["n", "Personas", 1, 200],
              ["seed", "Seed", 0, Number.MAX_SAFE_INTEGER],
              ["gammaScale", "Gamma ×", 0],
            ] as const
          ).map(([field, label, min, max]) => (
            <label key={field} className="flex flex-col gap-1 text-[11px] text-text-variant">
              {label}
              <input
                type="number"
                min={min}
                {...(max === undefined ? {} : { max })}
                step={field === "gammaScale" ? 0.1 : 1}
                value={controls[field]}
                onChange={(event) =>
                  onControlsChange({ ...controls, [field]: Number(event.target.value) })
                }
                className={NUMBER_FIELD}
              />
            </label>
          ))}
          <label className="flex items-center gap-1.5 pb-1.5 text-[11px] text-text-variant">
            <input
              type="checkbox"
              checked={controls.compareBaseline}
              onChange={(event) =>
                onControlsChange({ ...controls, compareBaseline: event.target.checked })
              }
              className={`accent-[rgb(var(--primary))] ${FOCUS_RING}`}
            />
            compare with baseline
          </label>
          <button
            type="button"
            onClick={onGenerate}
            disabled={generating || controlsError !== null}
            className={`glow ml-auto flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-[13px] font-semibold text-on-primary transition-[background-color,transform] duration-150 ease-out hover:bg-primary-dim active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name={generating ? "hourglass_top" : "auto_awesome"} size={16} />
            {generating ? "Generating…" : "Generate"}
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-text-dim">
          Pins are do()-interventions: the pinned value is clamped and only downstream
          attributes react; upstream distributions do not update.
        </p>
        {controlsError ? (
          <p role="alert" className="mt-2 text-xs text-danger">
            {controlsError}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="mt-2 text-xs text-danger">
            {error.message}
            {error.key ? <span className="font-mono"> ({error.key})</span> : null}
          </p>
        ) : null}
      </div>
    </div>
  );
}
