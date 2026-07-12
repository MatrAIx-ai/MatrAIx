/**
 * Synthesis Studio: read-only browsing of the Persona Full DAG.
 *
 * Three panes: category overview graph → drill-down subgraph → detail rail.
 * Phase 1 of docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md.
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse } from "@/lib/types";
import {
  StudioGlassPanel,
  StudioMeshShell,
  StudioPageFrame,
  StudioPageHeader,
} from "../studio/StudioShell";

export function SynthesisStudioView() {
  const overviewQuery = useQuery<SynthesisOverviewResponse>({
    queryKey: ["synthesis", "overview"],
    queryFn: api.getSynthesisOverview,
    staleTime: Infinity,
  });
  const overview = overviewQuery.data ?? null;

  return (
    <StudioMeshShell>
      <StudioPageFrame>
        <StudioPageHeader
          eyebrow="MatrAIx · Synthesis"
          title="Persona DAG Studio"
          subtitle={
            overview
              ? `${overview.counts.graphNodes.toLocaleString()} nodes · ${overview.counts.directedEdges.toLocaleString()} directed edges · ${overview.counts.categories} categories`
              : "Loading the Persona Full DAG…"
          }
        />
        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)_minmax(0,3fr)]">
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              {overviewQuery.isError
                ? "Failed to load the graph overview."
                : "Category overview (Task 5)"}
            </div>
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              Drill-down subgraph (Task 6)
            </div>
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">Details</div>
          </StudioGlassPanel>
        </div>
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default SynthesisStudioView;
