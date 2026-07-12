/**
 * Circular category-level overview of the Persona Full DAG.
 *
 * Categories are placed clockwise from the top by average topological order,
 * so proposal flow reads roughly clockwise. Node size encodes attribute
 * count; aggregated cross-category edges curve through the middle with
 * width/opacity by edge count. Identity is carried by the always-on labels;
 * color is reserved for hover/selection (design-token primary).
 */
import { useMemo, useState } from "react";

import type { SynthesisCategoryEdge, SynthesisOverviewResponse } from "@/lib/types";

const SIZE = 720;
const CENTER = SIZE / 2;
const RING_RADIUS = SIZE / 2 - 120;
const MIN_NODE_R = 7;
const MAX_NODE_R = 22;
const LABEL_GAP = 10;
const LABEL_MAX_CHARS = 20;
const MIN_HIT_R = 22;
const HIT_PADDING = 10;

interface PlacedCategory {
  name: string;
  x: number;
  y: number;
  r: number;
  angle: number;
  attributeCount: number;
  nodeCount: number;
}

function truncate(text: string): string {
  return text.length > LABEL_MAX_CHARS ? `${text.slice(0, LABEL_MAX_CHARS - 1)}…` : text;
}

export function CategoryOverviewGraph({
  overview,
  selectedCategory,
  onSelectCategory,
}: {
  overview: SynthesisOverviewResponse;
  selectedCategory: string | null;
  onSelectCategory: (name: string | null) => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [focused, setFocused] = useState<string | null>(null);

  const placed = useMemo(() => {
    const categories = overview.categories;
    const maxAttr = Math.max(1, ...categories.map((c) => c.attributeCount));
    const byName = new Map<string, PlacedCategory>();
    categories.forEach((cat, i) => {
      const angle = -Math.PI / 2 + (i / categories.length) * Math.PI * 2;
      byName.set(cat.name, {
        name: cat.name,
        x: CENTER + RING_RADIUS * Math.cos(angle),
        y: CENTER + RING_RADIUS * Math.sin(angle),
        r: MIN_NODE_R + (MAX_NODE_R - MIN_NODE_R) * Math.sqrt(cat.attributeCount / maxAttr),
        angle,
        attributeCount: cat.attributeCount,
        nodeCount: cat.nodeCount,
      });
    });
    return byName;
  }, [overview]);

  const maxEdgeCount = useMemo(
    () => Math.max(1, ...overview.edges.map((e) => e.count)),
    [overview],
  );

  const focus = hovered ?? focused ?? selectedCategory;

  function edgePath(edge: SynthesisCategoryEdge): string {
    const s = placed.get(edge.source);
    const t = placed.get(edge.target);
    if (!s || !t) return "";
    const midX = (s.x + t.x) / 2;
    const midY = (s.y + t.y) / 2;
    // Pull the control point 45% of the way toward the ring center so
    // long-range edges arc through the middle instead of hugging the rim.
    const cx = midX + (CENTER - midX) * 0.45;
    const cy = midY + (CENTER - midY) * 0.45;
    return `M ${s.x} ${s.y} Q ${cx} ${cy} ${t.x} ${t.y}`;
  }

  function selectCategory(name: string, isSelected: boolean): void {
    onSelectCategory(isSelected ? null : name);
  }

  return (
    <div className="h-full min-h-0 w-full overflow-auto">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        width={SIZE}
        height={SIZE}
        className="block max-w-none"
        role="img"
        aria-label="Persona DAG category overview"
        onClick={() => onSelectCategory(null)}
      >
        {/* Edges under nodes. Non-focused edges are recessive. */}
        <g fill="none">
          {overview.edges.map((edge) => {
            const active = focus !== null && (edge.source === focus || edge.target === focus);
            const width = 0.8 + 2.4 * Math.sqrt(edge.count / maxEdgeCount);
            return (
              <path
                key={`${edge.source}->${edge.target}`}
                d={edgePath(edge)}
                style={{
                  stroke: active ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeOpacity: focus === null ? 0.28 : active ? 0.85 : 0.08,
                  strokeWidth: active ? width + 0.6 : width,
                  transition: "stroke-opacity 150ms ease-out",
                }}
              />
            );
          })}
        </g>
        {/* Category nodes + labels. */}
        {[...placed.values()].map((cat) => {
          const isFocus = focus === cat.name;
          const isSelected = selectedCategory === cat.name;
          const rightSide = Math.cos(cat.angle) >= 0;
          const labelX = cat.x + (cat.r + LABEL_GAP) * Math.cos(cat.angle);
          const labelY = cat.y + (cat.r + LABEL_GAP) * Math.sin(cat.angle);
          const accessibleLabel = `${cat.name} — ${cat.attributeCount} attributes / ${cat.nodeCount} nodes`;
          return (
            <g
              key={cat.name}
              className="cursor-pointer"
              role="button"
              tabIndex={0}
              aria-label={accessibleLabel}
              aria-pressed={isSelected}
              onPointerEnter={() => setHovered(cat.name)}
              onPointerLeave={() => setHovered(null)}
              onFocus={() => setFocused(cat.name)}
              onBlur={() => setFocused(null)}
              onClick={(event) => {
                event.stopPropagation();
                selectCategory(cat.name, isSelected);
              }}
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                event.stopPropagation();
                selectCategory(cat.name, isSelected);
              }}
            >
              <title>{accessibleLabel}</title>
              <circle
                cx={cat.x}
                cy={cat.y}
                r={Math.max(MIN_HIT_R, cat.r + HIT_PADDING)}
                fill="transparent"
              />
              <circle
                cx={cat.x}
                cy={cat.y}
                r={cat.r}
                style={{
                  fill: isFocus
                    ? "rgb(var(--primary) / 0.18)"
                    : "rgb(var(--surface-high))",
                  stroke:
                    isFocus || isSelected ? "rgb(var(--primary))" : "rgb(var(--outline))",
                  strokeWidth: isSelected ? 2 : 1.2,
                  transition: "fill 150ms ease-out, stroke 150ms ease-out",
                }}
              />
              <text
                x={labelX}
                y={labelY}
                textAnchor={rightSide ? "start" : "end"}
                dominantBaseline="middle"
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  fill:
                    isFocus || isSelected
                      ? "rgb(var(--text-main))"
                      : "rgb(var(--text-dim))",
                }}
              >
                {truncate(cat.name)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
