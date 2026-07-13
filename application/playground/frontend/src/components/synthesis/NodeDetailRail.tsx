/**
 * Detail rail for one graph node: values with prior bars, and the
 * strongest incoming/outgoing edges (click to jump).
 */
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SynthesisNodeDetail, SynthesisNodeEdgeView } from "@/lib/types";
import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";

function EdgeList({
  title,
  edges,
  onJumpToNode,
  onAdjustEdge,
}: {
  title: string;
  edges: SynthesisNodeEdgeView[];
  onJumpToNode: (id: string) => void;
  onAdjustEdge?: (edgeId: string, edgeLabel: string) => void;
}) {
  if (edges.length === 0) return null;
  return (
    <div>
      <div className="hud mb-1 text-text-dim">{title}</div>
      <ul className="space-y-0.5">
        {edges.map((edge) => (
          <li key={edge.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onJumpToNode(edge.id)}
              className={`flex min-w-0 flex-1 items-baseline justify-between gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-surface-low motion-reduce:transition-none ${FOCUS_RING}`}
            >
              <span className="min-w-0 truncate text-xs text-text-variant">{edge.label}</span>
              <span className="flex-none font-mono text-[10px] text-text-dim">
                w {edge.weight}
              </span>
            </button>
            {onAdjustEdge ? (
              <button
                type="button"
                aria-label={`Adjust weight for edge with ${edge.label}`}
                title="Adjust edge weight"
                onClick={() => onAdjustEdge(edge.id, edge.label)}
                className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
              >
                <Sym name="tune" size={13} />
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function NodeDetailRail({
  nodeId,
  onJumpToNode,
  onPinValue,
  onAdjustPrior,
  onAdjustEdge,
}: {
  nodeId: string;
  onJumpToNode: (id: string) => void;
  onPinValue?: (nodeId: string, label: string, value: string) => void;
  onAdjustPrior?: (nodeId: string, label: string, values: string[], prior: number[]) => void;
  onAdjustEdge?: (
    source: string,
    target: string,
    sourceLabel: string,
    targetLabel: string,
  ) => void;
}) {
  const detailQuery = useQuery<SynthesisNodeDetail>({
    queryKey: ["synthesis", "node", nodeId],
    queryFn: () => api.getSynthesisNode(nodeId),
    staleTime: Infinity,
  });
  const detail = detailQuery.data ?? null;

  if (detailQuery.isError) {
    return (
      <div role="alert" className="grid h-full place-items-center text-sm text-danger">
        Failed to load node detail.
      </div>
    );
  }
  if (!detail) {
    return (
      <div role="status" className="grid h-full place-items-center text-sm text-text-dim">
        Loading…
      </div>
    );
  }

  const maxPrior = Math.max(0.0001, ...detail.prior);
  return (
    <div className="custom-scrollbar flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="hud text-text-dim">{detail.type}</div>
        <h3 className="font-display text-base text-text-main">{detail.label}</h3>
        <p className="font-mono text-[11px] text-text-dim">{detail.id}</p>
        <p className="mt-1 text-xs text-text-dim">
          {detail.category} · in {detail.inDegree} / out {detail.outDegree}
        </p>
        {detail.description ? (
          <p className="mt-2 text-xs leading-relaxed text-text-variant">{detail.description}</p>
        ) : null}
      </div>
      {detail.values.length > 0 ? (
        <div>
          <div className="mb-1 flex items-center justify-between">
            <div className="hud text-text-dim">Base prior</div>
            {onAdjustPrior ? (
              <button
                type="button"
                onClick={() =>
                  onAdjustPrior(detail.id, detail.label, detail.values, detail.prior)
                }
                className={`rounded px-1.5 py-0.5 text-[10px] text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
              >
                Adjust prior
              </button>
            ) : null}
          </div>
          <ul className="space-y-1">
            {detail.values.map((value, index) => {
              const prior = detail.prior[index] ?? 0;
              return (
                <li key={`${index}:${value}`} className="flex items-center gap-2">
                  <span className="w-28 flex-none truncate text-xs text-text-variant" title={value}>
                    {value}
                  </span>
                  <span className="h-2 min-w-0 flex-1 rounded-sm bg-surface-high" aria-hidden="true">
                    <span
                      className="block h-full rounded-sm"
                      style={{
                        width: `${Math.round((prior / maxPrior) * 100)}%`,
                        background: "rgb(var(--primary) / 0.55)",
                      }}
                    />
                  </span>
                  <span className="w-12 flex-none text-right font-mono text-[10px] text-text-dim">
                    {(prior * 100).toFixed(1)}%
                  </span>
                  {onPinValue ? (
                    <button
                      type="button"
                      aria-label={`Pin ${detail.label} to ${value}`}
                      title="Pin this value"
                      onClick={() => onPinValue(detail.id, detail.label, value)}
                      className={`grid h-6 w-6 flex-none place-items-center rounded text-text-dim transition-colors hover:bg-surface hover:text-primary motion-reduce:transition-none ${FOCUS_RING}`}
                    >
                      <Sym name="push_pin" size={13} />
                    </button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
      <EdgeList
        title="Strongest incoming"
        edges={detail.inEdges}
        onJumpToNode={onJumpToNode}
        onAdjustEdge={
          onAdjustEdge
            ? (edgeId, edgeLabel) =>
                onAdjustEdge(edgeId, detail.id, edgeLabel, detail.label)
            : undefined
        }
      />
      <EdgeList
        title="Strongest outgoing"
        edges={detail.outEdges}
        onJumpToNode={onJumpToNode}
        onAdjustEdge={
          onAdjustEdge
            ? (edgeId, edgeLabel) =>
                onAdjustEdge(detail.id, edgeId, detail.label, edgeLabel)
            : undefined
        }
      />
    </div>
  );
}
