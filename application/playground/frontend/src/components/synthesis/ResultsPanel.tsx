/**
 * Panel 5 — "Results": sampled personas as category-grouped cards with
 * lazily rendered natural-language text, plus the baseline-vs-adjusted
 * distribution comparison tab and the graph-overlay selector.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisOverviewResponse, SynthesisSampleResponse } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";
import { DistributionCompare } from "./DistributionCompare";

type TabId = "personas" | "distribution";
const PERSONAS_PER_PAGE = 10;

function personaCacheKey(persona: Record<string, string>): string {
  return JSON.stringify(
    Object.entries(persona).sort(([left], [right]) => left.localeCompare(right)),
  );
}

/** id → {label, category} lookup built from the overview payload. */
function useAttributeIndex(overview: SynthesisOverviewResponse | null) {
  return useMemo(() => {
    const index = new Map<string, { label: string; category: string }>();
    for (const category of overview?.categories ?? []) {
      for (const attribute of category.attributes) {
        index.set(attribute.id, { label: attribute.label, category: category.name });
      }
    }
    return index;
  }, [overview]);
}

function PersonaCard({
  persona,
  index,
  attributeIndex,
  pinnedIds,
  overlayActive,
  onToggleOverlay,
  overlayEnabled,
}: {
  persona: Record<string, string>;
  index: number;
  attributeIndex: Map<string, { label: string; category: string }>;
  pinnedIds: ReadonlySet<string>;
  overlayActive: boolean;
  onToggleOverlay: () => void;
  overlayEnabled: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const cacheKey = useMemo(() => personaCacheKey(persona), [persona]);
  const textQuery = useQuery({
    queryKey: ["synthesis", "render", cacheKey],
    queryFn: () => api.renderSynthesisPersona(persona),
    enabled: expanded,
    staleTime: Infinity,
  });

  const grouped = useMemo(() => {
    const groups = new Map<string, { id: string; label: string; value: string }[]>();
    for (const [id, value] of Object.entries(persona)) {
      const meta = attributeIndex.get(id);
      const category = meta?.category ?? "Other";
      const bucket = groups.get(category) ?? [];
      bucket.push({ id, label: meta?.label ?? id, value });
      groups.set(category, bucket);
    }
    return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
  }, [persona, attributeIndex]);
  const pinnedCategories = useMemo(
    () =>
      grouped
        .filter(([, attributes]) => attributes.some((item) => pinnedIds.has(item.id)))
        .map(([category]) => category),
    [grouped, pinnedIds],
  );
  const pinnedCategoryKey = JSON.stringify(pinnedCategories);
  const previousPinnedCategories = useRef(new Set(pinnedCategories));
  const [openCategories, setOpenCategories] = useState<Set<string>>(
    () => new Set(pinnedCategories),
  );

  useEffect(() => {
    const nextPinnedCategories = new Set(pinnedCategories);
    const newlyPinnedCategories = pinnedCategories.filter(
      (category) => !previousPinnedCategories.current.has(category),
    );
    previousPinnedCategories.current = nextPinnedCategories;
    if (newlyPinnedCategories.length === 0) return;

    setOpenCategories((previous) => {
      const next = new Set(previous);
      for (const category of newlyPinnedCategories) next.add(category);
      return next;
    });
    // The normalized primitive changes only when pinned category membership changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pinnedCategoryKey]);

  const toggleCategory = (category: string) => {
    setOpenCategories((previous) => {
      const next = new Set(previous);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  };

  return (
    <li
      data-testid="synthesis-persona-card"
      className="rounded-lg border border-outline-dim bg-surface-low/50"
      style={{ contentVisibility: "auto", containIntrinsicSize: "240px" }}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="hud text-text-dim">Persona #{index + 1}</span>
        <span className="min-w-0 flex-1" />
        {overlayEnabled ? (
          <button
            type="button"
            onClick={onToggleOverlay}
            aria-pressed={overlayActive}
            className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] transition-colors motion-reduce:transition-none ${
              overlayActive
                ? "bg-primary/15 text-primary"
                : "text-text-dim hover:bg-surface hover:text-text-main"
            } ${FOCUS_RING}`}
          >
            <Sym name="layers" size={13} />
            {overlayActive ? "Overlaying" : "Overlay"}
          </button>
        ) : null}
        <button
          type="button"
          onClick={() => setExpanded((previous) => !previous)}
          aria-expanded={expanded}
          className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
        >
          <Sym name={expanded ? "expand_less" : "notes"} size={13} />
          {expanded ? "Hide text" : "Text"}
        </button>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 px-3 pb-3">
        {grouped.map(([category, attributes]) => (
          <div key={category} className="min-w-[180px] max-w-full flex-1">
            <button
              type="button"
              aria-expanded={openCategories.has(category)}
              onClick={() => toggleCategory(category)}
              className={`hud mb-0.5 flex w-full items-center justify-between rounded text-left text-[9px] text-text-dim ${FOCUS_RING}`}
            >
              <span>{category}</span>
              <span>{attributes.length}</span>
            </button>
            {openCategories.has(category) ? (
              <ul className="space-y-0.5">
                {attributes.map((attribute) => (
                  <li key={attribute.id} className="flex items-baseline gap-1.5 text-[11px]">
                    {pinnedIds.has(attribute.id) ? (
                      <>
                        <Sym name="push_pin" size={11} className="translate-y-0.5 text-warn" />
                        <span className="sr-only">Pinned.</span>
                      </>
                    ) : null}
                    <span className="truncate text-text-dim" title={attribute.id}>
                      {attribute.label}
                    </span>
                    <span className="truncate font-mono text-text-variant" title={attribute.value}>
                      {attribute.value}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
      </div>
      {expanded ? (
        <div className="border-t border-outline-dim px-3 py-2 text-xs leading-relaxed text-text-variant">
          {textQuery.isError ? (
            <span role="status" aria-live="polite" aria-atomic="true" className="text-danger">
              Failed to render text.
            </span>
          ) : !textQuery.data ? (
            <span role="status" aria-live="polite" aria-atomic="true">
              Rendering…
            </span>
          ) : (
            <span className="whitespace-pre-line">{textQuery.data.text}</span>
          )}
        </div>
      ) : null}
    </li>
  );
}

export function ResultsPanel({
  result,
  overview,
  pinnedIds,
  overlayIndex,
  onOverlayIndexChange,
  overlayEnabled = false,
}: {
  result: SynthesisSampleResponse | null;
  overview: SynthesisOverviewResponse | null;
  pinnedIds: ReadonlySet<string>;
  overlayIndex: number | null;
  onOverlayIndexChange: (index: number | null) => void;
  overlayEnabled?: boolean;
}) {
  const [tab, setTab] = useState<TabId>("personas");
  const [page, setPage] = useState(0);
  const attributeIndex = useAttributeIndex(overview);

  useEffect(() => {
    setTab("personas");
    setPage(0);
  }, [result]);

  if (!result) {
    return (
      <div className="grid h-full place-items-center px-6 text-center text-sm text-text-dim">
        Generate a batch in the panel above to see personas here.
      </div>
    );
  }

  const tabs: readonly (readonly [TabId, string])[] = result.baselineMarginals
    ? [
        ["personas", `Personas (${result.personas.length})`],
        ["distribution", "Distribution"],
      ]
    : [["personas", `Personas (${result.personas.length})`]];
  const activeTab = tab === "distribution" && !result.baselineMarginals ? "personas" : tab;
  const totalPages = Math.max(1, Math.ceil(result.personas.length / PERSONAS_PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const pageStart = safePage * PERSONAS_PER_PAGE;
  const visiblePersonas = result.personas.slice(pageStart, pageStart + PERSONAS_PER_PAGE);

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, currentTab: TabId) => {
    const currentIndex = tabs.findIndex(([id]) => id === currentTab);
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    const nextTab = tabs[nextIndex]?.[0];
    if (!nextTab) return;
    setTab(nextTab);
    document.getElementById(`synthesis-results-tab-${nextTab}`)?.focus();
  };

  const renderPersonas = () => (
    <>
      <ul className="space-y-2">
        {visiblePersonas.map((persona, localIndex) => {
          const index = pageStart + localIndex;
          const cacheKey = personaCacheKey(persona);
          return (
            <PersonaCard
              key={`${index}:${cacheKey}`}
              persona={persona}
              index={index}
              attributeIndex={attributeIndex}
              pinnedIds={pinnedIds}
              overlayActive={overlayIndex === index}
              overlayEnabled={overlayEnabled}
              onToggleOverlay={() =>
                onOverlayIndexChange(overlayIndex === index ? null : index)
              }
            />
          );
        })}
      </ul>
      {totalPages > 1 ? (
        <nav
          aria-label="Persona result pages"
          className="mt-3 flex items-center justify-center gap-3"
        >
          <button
            type="button"
            disabled={safePage === 0}
            onClick={() => setPage((previous) => Math.max(0, previous - 1))}
            className={`rounded px-2 py-1 text-xs disabled:opacity-40 ${FOCUS_RING}`}
          >
            Previous
          </button>
          <span className="font-mono text-[11px] text-text-dim">
            {pageStart + 1}–
            {Math.min(pageStart + PERSONAS_PER_PAGE, result.personas.length)} of{" "}
            {result.personas.length}
          </span>
          <button
            type="button"
            disabled={safePage >= totalPages - 1}
            onClick={() =>
              setPage((previous) => Math.min(totalPages - 1, previous + 1))
            }
            className={`rounded px-2 py-1 text-xs disabled:opacity-40 ${FOCUS_RING}`}
          >
            Next
          </button>
        </nav>
      ) : null}
    </>
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        role="tablist"
        aria-label="Result views"
        aria-orientation="horizontal"
        className="flex flex-none items-center gap-1 border-b border-outline-dim px-3 py-2"
      >
        {tabs.map(([id, label]) => (
          <button
            key={id}
            id={`synthesis-results-tab-${id}`}
            type="button"
            role="tab"
            aria-selected={activeTab === id}
            aria-controls={`synthesis-results-panel-${id}`}
            tabIndex={activeTab === id ? 0 : -1}
            onClick={() => setTab(id)}
            onKeyDown={(event) => handleTabKeyDown(event, id)}
            className={`rounded-md px-3 py-1.5 text-xs transition-colors motion-reduce:transition-none ${
              activeTab === id
                ? "bg-primary/15 text-primary"
                : "text-text-dim hover:bg-surface hover:text-text-main"
            } ${FOCUS_RING}`}
          >
            {label}
          </button>
        ))}
        {overlayEnabled && overlayIndex !== null ? (
          <button
            type="button"
            onClick={() => onOverlayIndexChange(null)}
            className={`ml-auto flex items-center gap-1 rounded px-2 py-1 text-[11px] text-primary transition-colors hover:bg-primary/10 motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name="layers_clear" size={13} />
            Clear overlay (#{overlayIndex + 1})
          </button>
        ) : null}
      </div>
      <div
        id="synthesis-results-panel-personas"
        role="tabpanel"
        aria-labelledby="synthesis-results-tab-personas"
        hidden={activeTab !== "personas"}
        className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-3"
      >
        {activeTab === "personas" ? renderPersonas() : null}
      </div>
      {result.baselineMarginals ? (
        <div
          id="synthesis-results-panel-distribution"
          role="tabpanel"
          aria-labelledby="synthesis-results-tab-distribution"
          hidden={activeTab !== "distribution"}
          className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-3"
        >
          {activeTab === "distribution" ? <DistributionCompare result={result} /> : null}
        </div>
      ) : null}
    </div>
  );
}
