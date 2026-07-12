/**
 * Synthesis Studio: read-only browsing of the Persona Full DAG.
 *
 * Three panes: category overview graph → drill-down subgraph → detail rail.
 * Phase 1 of docs/superpowers/specs/2026-07-11-persona-dag-studio-design.md.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse } from "@/lib/types";
import { CategoryAttributeList } from "./CategoryAttributeList";
import { CategoryOverviewGraph } from "./CategoryOverviewGraph";
import {
  StudioGlassPanel,
  StudioMeshShell,
  StudioPageFrame,
  StudioPageHeader,
} from "../studio/StudioShell";

export function SynthesisStudioView() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [centerNode, setCenterNode] = useState<string | null>(null);
  const overviewQuery = useQuery<SynthesisOverviewResponse>({
    queryKey: ["synthesis", "overview"],
    queryFn: api.getSynthesisOverview,
    staleTime: Infinity,
  });
  const overview = overviewQuery.data ?? null;
  const selectedCategoryData =
    overview?.categories.find((cat) => cat.name === selectedCategory) ?? null;

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
            {overview ? (
              <CategoryOverviewGraph
                overview={overview}
                selectedCategory={selectedCategory}
                onSelectCategory={setSelectedCategory}
              />
            ) : (
              <div className="grid h-full place-items-center text-sm text-text-dim">
                {overviewQuery.isError ? "Failed to load the graph overview." : "Loading…"}
              </div>
            )}
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            <div className="grid h-full place-items-center text-sm text-text-dim">
              {centerNode ? `Drill-down: ${centerNode} (Task 6)` : "Drill-down subgraph (Task 6)"}
            </div>
          </StudioGlassPanel>
          <StudioGlassPanel className="min-h-[420px] overflow-hidden">
            {selectedCategoryData ? (
              <CategoryAttributeList
                key={selectedCategoryData.name}
                category={selectedCategoryData}
                onSelectAttribute={setCenterNode}
              />
            ) : (
              <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
                Click a category to list its attributes.
              </div>
            )}
          </StudioGlassPanel>
        </div>
      </StudioPageFrame>
    </StudioMeshShell>
  );
}

export default SynthesisStudioView;
