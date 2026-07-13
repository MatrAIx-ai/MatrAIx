/** Baseline-vs-adjusted marginal comparison (rows filled in by Task 10). */
import type { SynthesisSampleResponse } from "@/lib/types";

export function DistributionCompare({ result }: { result: SynthesisSampleResponse }) {
  if (!result.baselineMarginals) {
    return (
      <p className="px-3 py-4 text-sm text-text-dim">
        Enable “compare with baseline” before generating to see distribution shifts.
      </p>
    );
  }
  return (
    <p className="px-3 py-4 text-sm text-text-dim">
      Distribution comparison arrives with the next task.
    </p>
  );
}
