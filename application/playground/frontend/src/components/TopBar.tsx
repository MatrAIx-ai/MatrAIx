/**
 * TopBar: MatrAIx application header.
 *
 * Nav: Home · Playground · Runs · Persona World · Synthesis.
 */
import { PreflightChip } from "./PreflightChip";
import { FOCUS_RING } from "./cockpit/cockpitShared";
import { MatrAIxLogo } from "./studio/MatrAIxLogo";
import { useTheme } from "@/hooks/useTheme";

export type StudioMode = "home" | "playground";

export interface TopBarProps {
  mode: StudioMode;
  onModeChange: (mode: StudioMode) => void;
  runsActive: boolean;
  storeActive: boolean;
  synthesisActive: boolean;
  onOpenHome: () => void;
  onOpenRuns: () => void;
  onOpenPersonaStore: () => void;
  onOpenSynthesis: () => void;
}

function ThemeIcon({ showSun }: { showSun: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {showSun ? (
        <>
          <circle cx="12" cy="12" r="3.75" />
          <path d="M12 2.25v2M12 19.75v2M4.25 12h-2M21.75 12h-2M5.1 5.1l1.4 1.4M17.5 17.5l1.4 1.4M18.9 5.1l-1.4 1.4M6.5 17.5l-1.4 1.4" />
        </>
      ) : (
        <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
      )}
    </svg>
  );
}

export function TopBar({
  mode,
  onModeChange,
  runsActive,
  storeActive,
  synthesisActive,
  onOpenHome,
  onOpenRuns,
  onOpenPersonaStore,
  onOpenSynthesis,
}: TopBarProps) {
  const { theme, toggle } = useTheme();
  const nextIsLight = theme === "dark";

  const nav: Array<{ key: string; label: string; active: boolean; onClick: () => void }> = [
    {
      key: "home",
      label: "Home",
      active: mode === "home" && !runsActive && !storeActive && !synthesisActive,
      onClick: onOpenHome,
    },
    {
      key: "playground",
      label: "Playground",
      active: mode === "playground" && !runsActive && !storeActive && !synthesisActive,
      onClick: () => onModeChange("playground"),
    },
    { key: "runs", label: "Runs", active: runsActive, onClick: onOpenRuns },
    { key: "store", label: "Persona World", active: storeActive, onClick: onOpenPersonaStore },
    { key: "synthesis", label: "Synthesis", active: synthesisActive, onClick: onOpenSynthesis },
  ];

  return (
    <header className="relative z-20 flex-shrink-0 border-b border-outline bg-surface-lowest">
      <div className="flex h-14 items-center justify-between gap-4 px-5">
        <div className="flex min-w-0 items-center gap-8">
          <MatrAIxLogo size="md" onClick={onOpenHome} />
          <nav className="hidden h-14 items-stretch gap-7 text-[13px] font-medium md:flex" aria-label="Application">
            {nav.map(({ key, label, active, onClick }) => (
              <button
                key={key}
                type="button"
                onClick={onClick}
                aria-current={active ? "page" : undefined}
                className={`flex h-14 items-center border-b-2 transition-colors ${FOCUS_RING} ${
                  active
                    ? "border-primary text-primary"
                    : "border-transparent text-text-variant hover:text-text-main"
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex flex-shrink-0 items-center gap-2.5">
          <PreflightChip />

          <button
            type="button"
            onClick={toggle}
            aria-label={nextIsLight ? "Switch to light theme" : "Switch to dark theme"}
            title="Toggle light / dark"
            className={`grid h-9 w-9 flex-none place-items-center rounded-md border border-outline text-text-variant transition hover:border-primary hover:text-text-main active:scale-95 ${FOCUS_RING}`}
          >
            <ThemeIcon showSun={nextIsLight} />
          </button>
        </div>
      </div>
    </header>
  );
}
