/**
 * Baseline-vs-adjusted marginal comparison. TVD = 0.5 * Σ|p - q| per
 * attribute; rows with TVD > 0.01 render, sorted most-shifted first.
 */
import { useMemo } from "react";

import type { SynthesisSampleResponse } from "@/lib/types";

const TVD_THRESHOLD = 0.01;

interface ShiftRow {
  id: string;
  label: string;
  values: string[];
  baseline: number[];
  adjusted: number[];
  tvd: number;
}

function Bar({ share, muted }: { share: number; muted: boolean }) {
  return (
    <span
      className="block h-1.5 w-full min-w-0 flex-none rounded-sm bg-surface-high"
      aria-hidden="true"
    >
      <span
        className="block h-full rounded-sm"
        style={{
          width: `${Math.round(share * 100)}%`,
          background: muted ? "rgb(var(--outline))" : "rgb(var(--primary) / 0.65)",
        }}
      />
    </span>
  );
}

export function DistributionCompare({ result }: { result: SynthesisSampleResponse }) {
  const rows = useMemo<ShiftRow[]>(() => {
    const baseline = result.baselineMarginals;
    if (!baseline) return [];
    const shifted: ShiftRow[] = [];
    for (const [id, adjusted] of Object.entries(result.marginals)) {
      const base = baseline[id];
      if (!base) continue;
      const tvd =
        0.5 *
        adjusted.freqs.reduce(
          (sum, freq, index) => sum + Math.abs(freq - (base.freqs[index] ?? 0)),
          0,
        );
      if (tvd <= TVD_THRESHOLD) continue;
      shifted.push({
        id,
        label: adjusted.label,
        values: adjusted.values,
        baseline: base.freqs,
        adjusted: adjusted.freqs,
        tvd,
      });
    }
    return shifted.sort((left, right) => right.tvd - left.tvd);
  }, [result]);

  if (!result.baselineMarginals) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        Enable “compare with baseline” before generating to see distribution shifts.
      </p>
    );
  }
  if (rows.length === 0) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        No attribute shifted by more than {TVD_THRESHOLD} total variation distance.
      </p>
    );
  }

  return (
    <div className="min-w-0 space-y-4">
      <p className="text-[11px] leading-relaxed text-text-dim">
        {rows.length} attributes shifted (TVD &gt; {TVD_THRESHOLD}), most affected first.
        Grey bars: baseline · cyan bars: adjusted.
      </p>
      {rows.map((row) => (
        <section
          key={row.id}
          className="min-w-0 rounded-lg border border-outline-dim bg-surface-low/50 p-3"
          style={{ contentVisibility: "auto", containIntrinsicSize: "180px" }}
        >
          <div className="mb-1.5 flex items-baseline justify-between gap-2">
            <h4 className="min-w-0 truncate text-xs text-text-main" title={row.id}>
              {row.label}
            </h4>
            <span className="flex-none font-mono text-[10px] text-text-dim">
              TVD {row.tvd.toFixed(3)}
            </span>
          </div>
          <ul className="space-y-1.5">
            {row.values.map((value, index) => {
              const base = row.baseline[index] ?? 0;
              const adjusted = row.adjusted[index] ?? 0;
              const delta = adjusted - base;
              return (
                <li
                  key={`${index}:${value}`}
                  className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1 text-[11px] sm:grid-cols-[7rem_minmax(3rem,1fr)_auto]"
                >
                  <span className="min-w-0 truncate text-text-variant" title={value}>
                    {value}
                  </span>
                  <span className="col-span-2 row-start-2 flex min-w-0 flex-col gap-0.5 sm:col-span-1 sm:col-start-2 sm:row-start-1">
                    <Bar share={base} muted />
                    <Bar share={adjusted} muted={false} />
                  </span>
                  <span className="col-start-2 row-start-1 whitespace-nowrap text-right font-mono text-[10px] text-text-dim sm:col-start-3">
                    {(base * 100).toFixed(1)}% → {(adjusted * 100).toFixed(1)}%
                    {delta === 0 ? null : (
                      <span className={delta > 0 ? "text-primary" : "text-danger"}>
                        {" "}
                        {delta > 0 ? "↑" : "↓"}
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
