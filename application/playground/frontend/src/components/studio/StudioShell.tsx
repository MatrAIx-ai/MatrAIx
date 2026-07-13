import { useRef, useState, type ReactNode } from "react";

import { FOCUS_RING, Sym } from "../cockpit/cockpitShared";

/** Cockpit-style mesh background wrapper for Home, Runs, Persona World, etc. */
export function StudioMeshShell({ children }: { children: ReactNode }) {
  return (
    <div className="cockpit-mesh-bg flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
  );
}

export interface StudioPageHeaderProps {
  eyebrow: string;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
  /** Tighter title block for dense list pages (Runs, etc.). */
  compact?: boolean;
}

export function StudioPageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
  meta,
  compact = false,
}: StudioPageHeaderProps) {
  return (
    <div
      className={`flex flex-wrap items-center gap-x-3 ${compact ? "mb-3 gap-y-1" : "mb-5 items-start gap-y-3"}`}
    >
      <div className="min-w-0 flex-1">
        <span className={`hud text-primary ${compact ? "text-[9px]" : "text-[10px]"}`}>{eyebrow}</span>
        <h1
          className={`font-display font-bold tracking-tight text-text-main ${
            compact ? "text-[20px] leading-tight" : "text-[22px]"
          }`}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            className={
              compact
                ? "mt-0.5 truncate text-[12px] leading-snug text-text-variant"
                : "mt-1.5 max-w-2xl text-[13px] leading-relaxed text-text-variant"
            }
          >
            {subtitle}
          </p>
        )}
      </div>
      {meta}
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StudioGlassPanel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`glass-panel overflow-hidden rounded-xl ${className}`}>{children}</div>;
}

/**
 * Glass panel with a title bar and an expand/restore toggle. The body sits at
 * a fixed medium height by default and grows to most of the viewport when
 * expanded; panels toggle independently.
 */
export function ExpandableStudioPanel({
  title,
  children,
  className = "",
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  return (
    <div ref={rootRef} className={className}>
      <StudioGlassPanel>
        <div className="flex items-center justify-between border-b border-outline-dim px-4 py-2">
          <span className="hud text-text-dim">{title}</span>
          <button
            type="button"
            aria-label={expanded ? "Restore panel" : "Expand panel"}
            title={expanded ? "Restore panel" : "Expand panel"}
            onClick={() => {
              setExpanded((previous) => {
                const next = !previous;
                if (next) {
                  requestAnimationFrame(() => {
                    const reduceMotion = window.matchMedia(
                      "(prefers-reduced-motion: reduce)",
                    ).matches;
                    rootRef.current?.scrollIntoView({
                      block: "nearest",
                      behavior: reduceMotion ? "auto" : "smooth",
                    });
                  });
                }
                return next;
              });
            }}
            className={`grid h-7 w-7 place-items-center rounded-md text-text-dim transition-colors hover:bg-surface hover:text-text-main motion-reduce:transition-none ${FOCUS_RING}`}
          >
            <Sym name={expanded ? "collapse_content" : "expand_content"} size={18} />
          </button>
        </div>
        <div
          className="min-h-0 overflow-hidden transition-[height] duration-300 ease-out motion-reduce:transition-none"
          style={{ height: expanded ? "80vh" : 380 }}
        >
          {children}
        </div>
      </StudioGlassPanel>
    </div>
  );
}

export function StudioPageFrame({ children }: { children: ReactNode }) {
  return (
    <div className="custom-scrollbar min-h-0 flex-1 overflow-auto">
      <div className="mx-auto w-full max-w-[1180px] px-5 py-6 xl:px-6 xl:py-7">{children}</div>
    </div>
  );
}

export function StudioToolbarButton({
  children,
  onClick,
  disabled,
  icon,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  icon?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 rounded-lg border border-outline/50 bg-surface/60 px-3 py-2 text-[12px] text-text-variant backdrop-blur transition ease-out hover:border-primary/40 hover:bg-surface hover:text-text-main active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-55 ${FOCUS_RING}`}
    >
      {icon && <Sym name={icon} size={16} className={disabled ? "" : ""} />}
      {children}
    </button>
  );
}
