# matrAIx Redesign — PersonaEval Workbench (Design Spec)

- **Date:** 2026-06-26
- **Status:** Draft for review
- **Target:** `applications/persona_eval/frontend` (React 18 · Vite · Tailwind 3 · TanStack Query)
- **Approved mockup:** a navigable, high-fidelity prototype of every surface + state lives at
  `.superpowers/brainstorm/<session>/content/app-redesign-v3.html` (dark + light, served via the
  superpowers brainstorming visual companion). This spec translates that mockup into the real app.

---

## 1. Summary

Re-skin the PersonaEval Workbench from its current light **"Executive Precision"** look to **"matrAIx"** —
a dark-first, restrained/professional "mission-control" aesthetic (cyan primary, mint secondary, corner-accent
panels, mono HUD micro-labels). This is a **pure frontend re-skin**: we change design tokens, base CSS, the icon
primitive, component `className`s, a small amount of UI-only state, and **all user-facing copy**. We do **not**
touch the data layer, hooks, API client, query keys, types, or component structure.

## 2. Goals

1. Adopt the matrAIx visual identity across **every surface**: app shell, Chat workbench, the PersonaEval
   cockpit (Chatbot / Survey / Web), Runs (list · debrief · compare), and the persona/item Catalog.
2. Ship **dark (default) + light** via a persisted `<html>.light` toggle; every token has both variants.
3. Make **all copy friendly and tutorial-first** for first-time users (see §01.4) — no engineer shorthand,
   no fake telemetry, no roleplay; restrained and honest.
4. Preserve **per-option fidelity**: each application type shows its own environment, knobs, pipeline, and
   results (Chatbot-only Harbor environment; RecAI-only Domain knob; per-app Selection/Agent/Resources; the
   3/3/4-node pipelines; chatbot vs survey vs web scoring).
5. Fill in the **states the current app lacks**: empty, warming/cold-start, running, error/timeout, preflight.

## 3. Non-goals

- No backend, data-layer, hook, API, or behavior changes. No new product features.
- No change to routing/URL state or the existing two-surface (Chat / PersonaEval) information architecture.
- The mockup's mobile frames describe **intended** responsive behavior; full responsiveness is an
  implementation task (§06.6), not a promise that the current desktop layout already reflows.

## 4. Design principles (condensed — full system in §01)

- **Dark-first, restrained mission-control.** Bordered panels + the `.panel` corner bracket carry structure;
  the single primary CTA per view may use `.glow`. No scanlines, no fake metrics.
- **Tokens as `rgb(var(--x)/<alpha-value>)`** so opacity utilities (`bg-primary/10`) work everywhere; dark on
  `:root`, light on `:root.light`.
- **Three faces:** Space Grotesk (display/headings + the `matrAIx` wordmark), Inter (UI), JetBrains Mono
  (data + uppercase `.hud` micro-labels).
- **Icons via `lucide-react`** through one primitive (replaces the Material Symbols web-font).
- **Copy is friendly, tutorial, honest, restrained** (§01.4) — a hard requirement; every surface section ships
  a before→after copy table.

## 5. How to read this document

§01 is the **foundation** (tokens, fonts, icons, theme toggle, global copy rules) and lands first. §02–§06 are
**per-surface re-skin specs**, each with concrete current→matrAIx mapping tables, the states to add, and a copy
rewrite table. §07 is the **implementation sequencing, risks, and QA plan**.

| § | Surface |
| --- | --- |
| 01 | Design system + global copy guidelines |
| 02 | App shell + Chat workbench |
| 03 | Cockpit — Chatbot (config · environment · pipeline · feed · scorecard) |
| 04 | Cockpit — Survey + Web |
| 05 | Runs — history · debrief · compare (option-aware) |
| 06 | Persona catalog + cross-cutting (states · responsive · accessibility) |
| 07 | Implementation plan — sequencing, risks, QA |


---

# 01 · Design system + global copy guidelines

This is the foundation every other section builds on. It swaps the current
**"Executive Precision"** tokens (`src/index.css:20-73`, `tailwind.config.ts:24-117`)
for the **matrAIx** dark-first token system, loads the three matrAIx type faces,
moves icons from the Material Symbols web-font to `lucide-react`, adds a
light/dark toggle, and sets the global copy rules.

**Scope guard:** this is a *reskin*. We change tokens, base CSS, the icon
primitive, and copy only. No data layer, hooks, query keys, or component
structure change. Component sections (02+) consume the new token names; they do
not redefine them.

---

## 0. What changes, what stays

| Concern | Action |
| --- | --- |
| Color palette (surfaces, text, primary, semantic) | **Replace** with matrAIx triplets (R G B), dark default + light variant |
| Font families | **Replace**: add Space Grotesk (display) + JetBrains Mono (mono is kept), reweight Inter |
| Icons | **Migrate** Material Symbols web-font → `lucide-react` (recommended, see §2) |
| Radii | **Replace** with matrAIx scale (sm 4 / DEFAULT 6 / md 8 / lg 10) |
| Custom shadows (`shadow-soft`/`shadow-pop`) | **Remove** — matrAIx leans on borders + the `.panel` bracket + `.glow`; dropdowns use Tailwind's built-in `shadow-2xl` |
| Named type scale (`font-body-md`, `text-display`, …) | **Remove** — matrAIx uses the three families + raw sizes + `.hud`; see rename map (§1.4) |
| Spacing scale & `maxWidth.thread` | **Keep** — layout-only, not part of the visual identity; keeping them minimizes churn |
| Light/dark toggle | **Add** — class on `<html>`, persisted (§3) |
| Data layer / hooks / API / types / component tree | **Unchanged** |

The headline win of the token shape change: every color becomes
`rgb(var(--x)/<alpha-value>)`, so opacity utilities work everywhere
(`bg-primary/10`, `border-secondary/25`, `bg-primary/.07`). The current tokens
are bare `var(--x)` hex values, so tints are impossible without arbitrary
values — matrAIx relies on tints heavily, so this is required, not cosmetic.

---

## 1. Token system (literal code)

### 1.1 `src/index.css` — variable blocks

Replace the entire `:root { … }` block (`src/index.css:20-73`) with the two
blocks below. Dark is the default (`:root`); light is opt-in (`:root.light`).
`color-scheme` is set so native scrollbars/controls match the theme.

```css
/* ===========================================================================
   PersonaEval — design tokens ("matrAIx")
   Dark-first "mission control". Tokens are "R G B" triplets, consumed via
   rgb(var(--x)/<alpha-value>) so every color supports opacity utilities.
   Dark is the default; .light on <html> swaps the ramp (see useTheme).
   =========================================================================== */
:root {
  color-scheme: dark;

  /* Surfaces — page → panels → inputs */
  --surface-lowest: 14 14 15;   /* header, rails, inset wells */
  --surface-dim: 19 19 20;      /* page background */
  --surface-low: 28 27 28;      /* secondary fills, hover */
  --surface: 32 31 32;          /* panels / cards */
  --surface-high: 42 42 43;     /* raised chips, icon tiles */
  --field: 13 13 14;            /* text inputs, code wells */

  /* Lines */
  --outline: 63 72 82;          /* default borders, scrollbar thumb */
  --outline-dim: 42 42 44;      /* hairlines, dividers */

  /* Brand */
  --primary: 0 163 255;         /* cyan — primary CTA, active nav, accents */
  --primary-dim: 0 98 157;      /* CTA hover */
  --on-primary: 4 18 29;        /* text/icon on primary fills */
  --secondary: 78 222 163;      /* mint — success / positive / "ready" */
  --secondary-dim: 0 165 114;   /* mint hover */

  /* Text */
  --text-main: 229 226 227;     /* headings, primary text */
  --text-variant: 190 199 212;  /* body, labels */
  --text-dim: 154 160 166;      /* captions, hints, placeholders */

  /* Status */
  --danger: 255 107 122;        /* errors, destructive, low scores */
  --warn: 242 181 59;           /* warnings, mid scores */

  /* Score ramp (evaluation results only) — derived from status + mint */
  --score-low: 255 107 122;     /* = danger */
  --score-mid: 242 181 59;      /* = warn */
  --score-high: 78 222 163;     /* = secondary (mint) */

  /* Type */
  --sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --display: "Space Grotesk", var(--sans);
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;

  /* Radii */
  --radius-sm: 4px;
  --radius: 6px;
  --radius-md: 8px;
  --radius-lg: 10px;
}

:root.light {
  color-scheme: light;

  --surface-lowest: 255 255 255;
  --surface-dim: 244 246 248;
  --surface-low: 238 241 244;
  --surface: 255 255 255;
  --surface-high: 231 236 241;
  --field: 237 241 245;

  --outline: 203 213 225;
  --outline-dim: 226 232 240;

  --primary: 0 118 194;
  --primary-dim: 0 92 152;
  --on-primary: 255 255 255;
  --secondary: 0 150 103;
  --secondary-dim: 0 120 84;

  --text-main: 17 23 31;
  --text-variant: 55 65 81;
  --text-dim: 100 116 139;

  --danger: 190 50 70;
  --warn: 176 120 16;

  --score-low: 190 50 70;
  --score-mid: 176 120 16;
  --score-high: 0 150 103;
}
```

### 1.2 `src/index.css` — base layer + utilities (literal)

Replace the `@layer base { … }` block and the foundational helpers
(`src/index.css:78-177`). Keep the three `@tailwind` directives at the top of
the file (`src/index.css:1-3`) and the motion `@layer utilities` block
(`src/index.css:182-215`) — those still apply. Drop the entire
`.material-symbols-outlined { … }` block (`src/index.css:146-161`); it is dead
once icons move to lucide.

```css
@layer base {
  * { @apply box-border; }

  html, body, #root { height: 100%; }

  body {
    font-family: var(--sans);
    color: rgb(var(--text-main));
    background: rgb(var(--surface-dim));
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  ::selection { background: rgb(var(--primary) / 0.25); }

  /* One tokenized focus ring on every interactive element. */
  :focus-visible {
    outline: 2px solid rgb(var(--primary));
    outline-offset: 2px;
  }

  /* Thin, theme-aware scrollbars everywhere. */
  * {
    scrollbar-width: thin;
    scrollbar-color: rgb(var(--outline)) transparent;
  }
  *::-webkit-scrollbar { width: 9px; height: 9px; }
  *::-webkit-scrollbar-track { background: transparent; }
  *::-webkit-scrollbar-thumb {
    background: rgb(var(--outline));
    border-radius: 9999px;
    border: 2px solid transparent;
    background-clip: padding-box;
  }
  *::-webkit-scrollbar-thumb:hover { background: rgb(var(--primary)); }
}

/* ---------------------------------------------------------------------------
   matrAIx utility classes. Written as plain CSS (NOT inside @layer) so they
   always ship and are never purged — matching the existing convention for
   .custom-scrollbar. Font-family helpers (.font-sans/.font-display/.font-mono)
   are NOT hand-written here; Tailwind generates them from fontFamily config.
   --------------------------------------------------------------------------- */

/* Mono, uppercase, letter-spaced micro-label (HUD). Pair with text-text-dim. */
.hud {
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

/* Bordered box with a top-left cyan corner bracket. Use on bg-surface panels. */
.panel { position: relative; }
.panel::before {
  content: "";
  position: absolute;
  top: -1px;
  left: -1px;
  width: 9px;
  height: 9px;
  border-top: 2px solid rgb(var(--primary));
  border-left: 2px solid rgb(var(--primary));
  pointer-events: none;
}

/* Cyan glow — RESERVED for the single primary CTA on a view (e.g. "Start run"). */
.glow { box-shadow: 0 10px 34px -10px rgb(var(--primary) / 0.5); }

/* Thin internal scrollbars for scroll panes (transcript, lists, code wells). */
.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgb(var(--outline));
  border-radius: 9px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgb(var(--primary)); }
```

The existing `@keyframes rb-pulse` / `rb-spin` and the
`prefers-reduced-motion` block (`src/index.css:182-215`) are kept verbatim —
they remain the warming/spinner animations and the matrAIx mockup also disables
motion under `prefers-reduced-motion`.

### 1.3 `tailwind.config.ts` (literal, drop-in)

Replace the whole file. Colors use `rgb(var(--x)/<alpha-value>)`; the named
font-size scale and custom shadows are removed; spacing + `maxWidth.thread` are
retained.

```ts
import type { Config } from "tailwindcss";

/**
 * Tailwind theme for PersonaEval — the "matrAIx" design system.
 * Dark-first; tokens live in src/index.css as "R G B" triplets and are
 * consumed via rgb(var(--x)/<alpha-value>) so opacity utilities (bg-primary/10)
 * work for every color. Three faces only: font-sans (Inter, default UI),
 * font-display (Space Grotesk, headings), font-mono (JetBrains Mono, data + HUD).
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "surface-lowest": "rgb(var(--surface-lowest) / <alpha-value>)",
        "surface-dim": "rgb(var(--surface-dim) / <alpha-value>)",
        "surface-low": "rgb(var(--surface-low) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-high": "rgb(var(--surface-high) / <alpha-value>)",
        field: "rgb(var(--field) / <alpha-value>)",

        outline: "rgb(var(--outline) / <alpha-value>)",
        "outline-dim": "rgb(var(--outline-dim) / <alpha-value>)",

        primary: "rgb(var(--primary) / <alpha-value>)",
        "primary-dim": "rgb(var(--primary-dim) / <alpha-value>)",
        "on-primary": "rgb(var(--on-primary) / <alpha-value>)",
        secondary: "rgb(var(--secondary) / <alpha-value>)",
        "secondary-dim": "rgb(var(--secondary-dim) / <alpha-value>)",

        "text-main": "rgb(var(--text-main) / <alpha-value>)",
        "text-variant": "rgb(var(--text-variant) / <alpha-value>)",
        "text-dim": "rgb(var(--text-dim) / <alpha-value>)",

        danger: "rgb(var(--danger) / <alpha-value>)",
        warn: "rgb(var(--warn) / <alpha-value>)",

        // Evaluation score ramp only (red → amber → mint).
        "score-low": "rgb(var(--score-low) / <alpha-value>)",
        "score-mid": "rgb(var(--score-mid) / <alpha-value>)",
        "score-high": "rgb(var(--score-high) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "10px",
        // `xl`, `2xl`, `full` fall through to Tailwind defaults.
      },
      // Layout-only; intentionally retained from the prior config.
      spacing: {
        xs: "4px", sm: "8px", md: "16px", lg: "24px", xl: "32px",
        unit: "4px", gutter: "16px", "container-max": "1440px",
      },
      maxWidth: { thread: "680px" },
    },
  },
  plugins: [],
} satisfies Config;
```

> **Note on `rgb(var(--x) / <alpha-value>)`:** keep the literal `<alpha-value>`
> placeholder string — Tailwind substitutes the opacity at build time. Without
> it, `bg-primary/10` silently produces solid color.

### 1.4 Token rename map (old → new)

Component sections (02+) find/replace using this table. Old names on the left
no longer exist after this section lands, so anything not migrated will fail the
build (which is the desired tripwire).

| Old token / utility | New matrAIx equivalent | Notes |
| --- | --- | --- |
| `bg-background`, `bg-surface`, `bg-surface-bright` | `bg-surface-dim` (page) / `bg-surface` (panels) | page vs panel split is now explicit |
| `bg-surface-container-lowest` | `bg-surface-lowest` | header, rails, inset wells |
| `bg-surface-container-low` | `bg-surface-low` | hover / secondary fill |
| `bg-surface-container` | `bg-surface` | panel body |
| `bg-surface-container-high(est)` | `bg-surface-high` | raised chip / icon tile |
| (text inputs) | `bg-field` | inputs/textareas/code wells use `field` now |
| `text-on-surface` | `text-text-main` | |
| `text-on-surface-variant` | `text-text-variant` (body) / `text-text-dim` (caption) | pick by emphasis |
| `border-border-soft`, `border-outline-variant` | `border-outline-dim` | hairlines |
| `border-outline` | `border-outline` | unchanged name, new value |
| `bg-primary-tint`, `text-on-primary-container` | `bg-primary/10`, `text-primary` | tints now via opacity |
| `bg-success`, `bg-success-container`, `text-on-success-container` | `text-secondary` / `bg-secondary/10` / `border-secondary/25` | success = mint |
| `bg-error*`, `text-on-error-container` | `text-danger` / `bg-danger/10` | |
| `bg-warning*`, `text-on-warning-container` | `text-warn` / `bg-warn/10` | |
| `text-score-low/mid/high` | `text-score-low/mid/high` | names kept, values re-derived |
| `font-display` (was Inter 24px) | `font-display text-2xl` | family + explicit size |
| `font-headline-md` / `-sm` | `font-display text-lg` / `font-semibold text-sm` | |
| `font-body-lg/md/sm` | `font-sans text-base/sm/[13px]` | family is default; just set size |
| `font-label-md` | `text-xs font-medium` | |
| `font-mono-sm` | `font-mono text-xs` | |
| (uppercase micro-labels) | `.hud text-[10px] text-text-dim` | new HUD treatment |
| `shadow-soft` | remove (rely on `border-outline`) | flat, bordered surfaces |
| `shadow-pop` | `shadow-2xl` | dropdowns/popovers |
| `.material-symbols-outlined`, `<Sym name="…">` | `<Icon name="…">` (lucide) | see §2 |

---

## 2. Fonts + icon strategy

### 2.1 Fonts — `index.html`

Replace the two font `<link>`s currently in `index.html` (the Inter+JetBrains
line and the entire Material Symbols line) with the single matrAIx stylesheet
(same weights the mockup ships, `app-redesign-v3.html:9`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap"
  rel="stylesheet"
/>
```

- **Inter** → `font-sans`, the default UI face (body, controls, labels).
- **Space Grotesk** → `font-display`, headings + the `matrAIx` wordmark only.
- **JetBrains Mono** → `font-mono`, all machine data (IDs, scores, timings,
  JSON wells) and every `.hud` micro-label.

Removing the Material Symbols stylesheet drops a large render-blocking variable
web-font from first paint.

### 2.2 Icons — **recommendation: migrate to `lucide-react`**

The app currently renders Material Symbols glyphs through one primitive,
`Sym` (`src/components/cockpit/cockpitShared.tsx:54-67`), used via
`<Sym name="play_arrow" />`. The matrAIx mockup is built entirely on lucide
(`data-lucide="…"`, `app-redesign-v3.html:55`), and the matrAIx system mandates
"Icons via lucide".

**Recommended: `lucide-react`.** Rationale:
- It is the idiomatic React build of the exact icon set in the mockup, so glyphs
  match 1:1 (`play`, `check`, `scan-face`, `gauge`, `clipboard-check`, `globe`,
  `footprints`, …).
- Inline SVGs inherit `currentColor` and a configurable `stroke-width`, which
  fits the token system perfectly — `text-primary` colors an icon, themes swap
  automatically, and `strokeWidth={1.75}` reproduces the mockup's
  `[data-lucide]{stroke-width:1.75}` line weight.
- Tree-shakeable (only imported glyphs ship); removes the web-font request.

Keep the **single-primitive** pattern so call sites barely change. Reimplement
the primitive over lucide (rename `Sym` → `Icon`, or keep the export name) with
an explicit registry so the bundle stays tree-shaken:

```tsx
// src/components/cockpit/cockpitShared.tsx  (icon primitive, reskinned)
import { Play, Check, ScanFace, Gauge, ClipboardCheck, Globe /* …as used */ } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const ICONS = {
  play: Play, check: Check, "scan-face": ScanFace, gauge: Gauge,
  "clipboard-check": ClipboardCheck, globe: Globe, /* extend per component */
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

/** A single lucide glyph, sized + theme-colored via currentColor. */
export function Icon({
  name, size = 16, strokeWidth = 1.75, className = "", label,
}: { name: IconName; size?: number; strokeWidth?: number; className?: string; label?: string }) {
  const Glyph = ICONS[name];
  return (
    <Glyph
      size={size}
      strokeWidth={strokeWidth}
      className={className}
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
    />
  );
}
```

Migration notes for component sections:
- Each section swaps its Material Symbol names (snake_case, e.g. `play_arrow`,
  `check_circle`) to the lucide name (kebab-case, e.g. `play`, `check-circle-2`)
  and adds it to `ICONS` if missing.
- The old `fill` axis (0|1) has no lucide equivalent; for solid glyphs (e.g. the
  play triangle in the CTA) add `className="fill-current"` instead.
- `aria` behavior is preserved verbatim — icons stay decorative unless given a
  `label`, and are never the sole carrier of meaning.
- Add the dependency: `npm i lucide-react`. No other code depends on Material
  Symbols once `Sym`'s two references and the `index.css` block are removed.

---

## 3. Light/dark toggle mechanism

Dark is the default. Light is activated by adding the class `light` to the
`<html>` element (`document.documentElement`), exactly as the mockup does
(`app-redesign-v3.html:1365-1367`). Persisted in `localStorage`.

**Three pieces:**

**(a) Pre-paint boot script — `index.html` `<head>`** (before the module script)
to set the class before React mounts, avoiding a light/dark flash:

```html
<script>
  (function () {
    try {
      var t = localStorage.getItem("personaeval-theme");
      // Default dark; honor a stored 'light', or first-visit system preference.
      if (t === "light" || (!t && matchMedia("(prefers-color-scheme: light)").matches)) {
        document.documentElement.classList.add("light");
      }
    } catch (e) {}
  })();
</script>
```

**(b) A tiny hook — `src/hooks/useTheme.ts`** (new file; UI state only, touches
nothing in the data layer):

```ts
import { useCallback, useState } from "react";

const KEY = "personaeval-theme";
export type Theme = "dark" | "light";

function current(): Theme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current);
  const toggle = useCallback(() => {
    const next: Theme = current() === "light" ? "dark" : "light";
    document.documentElement.classList.toggle("light", next === "light");
    try { localStorage.setItem(KEY, next); } catch {}
    setTheme(next);
  }, []);
  return { theme, toggle };
}
```

**(c) Wiring — the top app bar (App shell, owned by the shell section).** Add a
36px square ghost button at the right of the header, matching the mockup
(`app-redesign-v3.html:83-85`): `lucide` `sun` icon when in dark (tap → light),
`moon` when in light (tap → dark).

```tsx
const { theme, toggle } = useTheme();
// …
<button
  onClick={toggle}
  aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
  title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
  className="grid place-items-center w-9 h-9 rounded-md border border-outline
             text-text-variant hover:text-text-main hover:border-primary transition-colors"
>
  <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
</button>
```

Persistence key: `personaeval-theme` (`"dark" | "light"`). The hook reads live
from the DOM class so it stays in sync with the boot script; no context/provider
needed for a single toggle.

---

## 4. Global copy & UX-writing guidelines

**Hard requirement (from the user):** every user-facing string must help a
**first-time user** understand what is happening. We are writing for someone who
has never run a persona evaluation, not for the engineer who built it. The tone
stays restrained and professional — helpful, never cute, never chatty, no
roleplay, no fake telemetry.

### Principles

1. **Friendly & human, not machine shorthand.** Prefer a short sentence over a
   terse label fragment. "Scored on 3 dimensions" → "We score the chat on three
   things." Avoid stacking `·`-separated fragments as if they were a status line.
2. **Tutorial-first.** Assume the reader needs to learn the concept here. The
   first time a term appears in a view (persona, turn, constraint score, trace),
   say what it *means* in plain words, once.
3. **Honest.** Describe only what the system actually does. No invented
   telemetry, no "agents online", no progress theater. If something is a
   simulation, call it a simulation ("a simulated user").
4. **Restrained.** Professional register. No exclamation marks, no emoji in
   product copy, no jokes. Confident and calm, like good docs.
5. **HUD labels are real words.** `.hud` micro-labels are uppercase for *style*,
   but must be readable words — "GETTING READY", "LIVE", "PIPELINE", never
   "PREFLT" or cryptic abbreviations.
6. **Numbers get context.** A bare "8.4/10" means little to a newcomer; pair
   scores with what they measure ("Overall — how well the app met the user's
   goal"). Counts say what they count ("4 of 5 questions answered").
7. **Empty/error/loading states teach the next action.** Never a bare "No data"
   or "Error". Say what would fill the space and how to get there, or what went
   wrong and what to try.

### Before / after (drawn from the real app)

| Where | Before (engineer shorthand) | After (friendly, tutorial) |
| --- | --- | --- |
| Pipeline summary caption | `~8 turns · claude-haiku-4-5 persona · scored on 3 dimensions` | `A simulated user chats with the app for a few turns, then rates how well it understood and met their needs.` |
| Browser tab / `index.html` `<title>` | `PersonaEval — Workbench` | `PersonaEval — test your app with simulated users` |
| `<meta name="description">` | `PersonaEval — a developer harness to test interactive chatbot applications with simulated persona users.` | `Try out your chatbot, survey, or website against realistic simulated users and see how well it performs — before real people do.` |
| Engine status chip (`app-redesign-v3.html:80`) | `Engine ready` | `Ready to run` (tooltip: "The evaluation engine is warmed up. Pick your settings, then start a run.") |
| HUD micro-label, preflight (`app-redesign-v3.html:692`) | `STATE · PREFLIGHT` | `GETTING READY` |
| Primary CTA (`app-redesign-v3.html:87`) | `New run` | `New run` (keep — short and clear; tooltip: "Set up a fresh persona evaluation.") |

### New helper text (global / cross-cutting)

These are owned here because they recur across views; component sections reuse
them rather than reinventing.

- **First-run banner (dismissible, top of the setup view), shown until the first
  run completes:** "New here? PersonaEval runs your app against a simulated user
  — a 'persona' — and reports how well it did. Choose what to test below, then
  press *New run*."
- **Theme toggle tooltip:** "Switch to light theme" / "Switch to dark theme" (see §3).
- **Generic loading scaffold (any pane awaiting data):** heading "Working on it…"
  with subtext "Setting things up — this usually takes a few seconds." (Reuse the
  existing `rb-pulse`/spinner.)
- **Generic empty scaffold (no runs yet):** heading "Nothing here yet" with
  subtext "Your runs will show up here once you start one. Press *New run* to
  begin." and a primary button to the setup view.
- **Generic error scaffold (request failed):** heading "That didn't work" with
  subtext "Something went wrong reaching the evaluation engine. Check that it's
  running, then try again." and a "Try again" button wired to the existing retry
  (no behavior change — copy only).
- **Term tooltips (first appearance, info `i` affordance):**
  - *Persona* → "A simulated user with goals and preferences. We use it to act
    like a real person trying to get something done in your app."
  - *Turn* → "One back-and-forth message between the simulated user and your app."
  - *Constraint score* → "How well the app respected hard requirements the user
    stated (0–5)."
  - *Preference score* → "How well the app matched the user's softer likes and
    dislikes (0–5)."
  - *Trace* (web) → "A step-by-step recording of what the simulated user did in
    the browser — clicks, typing, and screenshots."

These global strings, term definitions, and state scaffolds are the contract;
each component section (chatbot / survey / web / runs / setup) localizes the rest
of its copy against these same principles and may cite these tooltips by term.


---

# 02 · App shell + Chat workbench

Reskin spec for the application **shell** (header, footer, theme) and the **Chat
three-pane workbench** (session rail · conversation thread · turn inspector ·
`>_` composer). This is a pure, in-place restyle: **every prop, hook, query,
mutation, handler and component boundary stays exactly as it is today.** What
changes is (1) the design tokens each `className` resolves to, (2) the typography
register, (3) a handful of layout wrappers (chat bubbles, inspector tabs), and
(4) two genuinely new, UI-only additions — a **light/dark theme toggle** and a
**slim footer**. No data-layer, behavior, or type changes.

> **Boundaries with sibling sections.** The literal CSS variables + `tailwind.config.ts`
> theme keys are owned by **§01 Design system** — this section only *consumes*
> those new utility names. The `ChatConfigBar` knobs and the `EnvironmentPopover`
> internals are owned by **§03 Config & environment**; here we only retoken the
> `ChatConfigBar` *container* (`ChatConfigBar.tsx:26`). The catalog drawer,
> RecommendationCard catalog contents, cockpit, and runs are other sections.

---

## 1. Reskin principles (apply to every table below)

1. **Keep structure.** Same files, same exports, same props. A row labeled
   "ADD" or "NEW" is the only place new code appears, and it is always
   presentational/UI state.
2. **Dark-first.** matrAIx ships dark by default (`:root` = dark tokens,
   `:root.light` = overrides, both defined in §01). The page is `bg-surface-dim`;
   header/rails/inspector/composer/footer are `bg-surface-lowest`; floating cards
   and bubbles are `bg-surface`; inputs are `bg-field`.
3. **Restrained.** One accent (`primary`, cyan) for state + interaction; `secondary`
   (mint) only for *positive/connected/done*; `warn`/`danger` for trouble. No
   scanlines, no faux telemetry, no roleplay copy. The `.glow` hero treatment is
   reserved for the cockpit's single "Run eval" CTA (§04) — **the chat shell uses
   `bg-primary` with no glow** so each surface has at most one hero.
4. **Never invent data.** The Chat workbench shows only what `TurnView` actually
   carries (plan, recommended items, native raw, latency). The new "Scores" tab
   (§4.B4) therefore teaches that scores come from a *PersonaEval run* rather than
   fabricating a 0–10 score on a manual turn.

### 1.1 Token & type translation (the backbone — every table references this)

| Current utility (today) | matrAIx utility | Where it lands |
|---|---|---|
| `bg-background`, `bg-surface` | `bg-surface-dim` | page / centre `<main>` |
| `bg-surface-container-lowest` | `bg-surface-lowest` | header, rails, inspector, composer bar, footer |
| `bg-surface-container-lowest` (a *card/popover/bubble*) | `bg-surface` | bubbles, readiness popover, inspector cards |
| `bg-surface-container-low` | `bg-surface-low` | rec item cards, secondary chips |
| `bg-surface-container` / `-high` / `-highest` | `bg-surface` / `bg-surface-high` | chips, skeleton fills |
| composer input fill (`bg-surface-container-lowest`) | `bg-field` | composer + any `<input>`/`<textarea>` |
| `text-on-surface` | `text-text-main` | primary text |
| `text-on-surface-variant` | `text-text-variant` | secondary text |
| `text-outline` (muted glyph/placeholder) | `text-text-dim` | tertiary text, placeholders |
| `placeholder:text-outline` | `placeholder:text-text-dim` | inputs |
| `border-border-soft` | `border-outline-dim` (faint divider) / `border-outline` (card edge) | dividers vs. card borders |
| `border-outline-variant` | `border-outline` | controls, chips |
| `bg-primary` / `text-on-primary` / `text-primary` | unchanged | CTAs, active accents |
| `hover:bg-primary-container` | `hover:bg-primary-dim` | primary hover |
| `bg-primary/10`, `bg-primary/5` | unchanged | active tints |
| `text-success` / `bg-success` / `bg-success-container` | `text-secondary` / `bg-secondary` / `bg-secondary/10` | positive/connected/done |
| `*-warning*` | `*-warn*` (`text-warn`, `bg-warn/10`, `border-warn/30`) | setup/cold-start |
| `*-error*` | `*-danger*` (`text-danger`, `bg-danger/10`, `border-danger/40`) | failures |
| `text-headline-md`/`font-headline-md` (heading) | `font-display font-bold tracking-tight` + explicit size (`text-[15px]`–`text-[22px]`) | titles, empty-state headlines |
| `text-headline-sm uppercase tracking-wider` (pane titles) | `.hud text-[10px]` | "Sessions", "Turn inspector", section labels |
| `text-body-md` / `text-body-sm` | `text-[13px]` / `text-[12px]` | body copy |
| `font-mono-sm`/`text-mono-sm` | `font-mono text-[11px]` | ids, scores, traces |
| `text-label-md uppercase tracking-wider` | `.hud` (`font-mono uppercase tracking-[.14em]`) + size | every micro-label |
| `rounded-xl` (composer), `rounded-lg` (popover) | `rounded-md` | calmer radii |
| `focus-visible:ring-offset-surface-container-lowest` (in `FOCUS_RING`, `cockpitShared.tsx:30`) | `…-offset-surface-lowest` | one shared edit |

**Utility classes** (defined in §01): `.panel` (cyan top-left corner bracket) on
discrete content cards only — the inspector's Trace/Output cards, the readiness
popover, the error/timeout card — **not** on structural rails/panes (that would be
noisy). `.hud` for every uppercase mono micro-label, always spelled as real words.
`.custom-scrollbar` stays on all three scroll regions. `.glow` not used in the chat
shell (see principle 3).

**Icons.** Components call `Sym name="…"` (Material Symbols, `cockpitShared.tsx:55`).
The icon *primitive + font* is a §01 decision (keep `Sym`/Material Symbols, or
add a thin lucide `<Icon>` wrapper). Either way the **intent** below holds; swap
glyphs to the lucide names matrAIx uses if §01 moves to lucide:

| Used as | Current `Sym` | lucide (matrAIx mockup) |
|---|---|---|
| assistant / bot | `smart_toy` | `brain-circuit` |
| chat / session | `forum` | `messages-square` |
| new / add | `add` | `plus` |
| search | `search` | `search` |
| send | `arrow_forward` | `arrow-up` |
| working / busy | `autorenew`,`more_horiz` | `loader-2` |
| retry | `refresh` | `refresh-cw` |
| inspect | `manage_search` | `search-code` |
| error | `error` | `alert-triangle` |
| check ok | `check`,`check_circle` | `check`,`circle-check` |
| theme dark/light | — (new) | `moon` / `sun` |

---

## 2. App shell

### 2.A Header — `TopBar.tsx`

Keeps its three zones (brand+search · surface tabs · right cluster) and all props
(`TopBar.tsx:21-38`). Swap the **PersonaEval brand lockup → the matrAIx wordmark**
(no version badge — there isn't one today, and none is added), retoken, and **ADD
the theme toggle** to the right cluster between the preflight chip and the session
actions.

| Element | Current (`TopBar.tsx`) | Target matrAIx | Notes |
|---|---|---|---|
| `<header>` | `border-b border-border-soft bg-surface-container-lowest …min-h-16` (`:61`) | `border-b border-outline bg-surface-lowest h-14` | keep flex-wrap responsive behavior |
| Wordmark | `<span class="…text-headline-md font-bold…text-primary">PersonaEval</span>` (`:64-66`) | `<span class="font-display font-bold text-[19px] tracking-tight text-text-main">matr<span class="text-primary">AI</span>x</span>` | brand = matrAIx; only `AI` is `text-primary`; **no version badge** |
| ⌘K search button | `rounded-full border-outline-variant bg-surface-container-low …text-outline hover:border-primary` (`:67-78`) | `rounded-md border-outline bg-surface-low text-text-dim hover:border-primary hover:text-text-variant`; label `text-text-variant`; `<kbd>` → `border-outline bg-surface font-mono text-[10px] text-text-variant` | unchanged `onOpenSearch`; keep `xl:flex` hide rule |
| Surface tabs (`Chat` / `PersonaEval`) | active `border-primary font-bold text-primary`; idle `border-transparent text-on-surface-variant hover:text-primary` (`:82-101`) | active `border-b-2 border-primary text-primary`; idle `border-b-2 border-transparent text-text-variant hover:text-text-main`; row `text-[13px] font-medium` | **keep exactly two tabs** — Runs lives inside PersonaEval, Catalog is the ⌘K drawer (matches current behavior); do not add nav items |
| Preflight chip | `<PreflightChip/>` (`:105`) | unchanged mount — restyled in §2.E | |
| **Theme toggle** | — | **ADD** `<ThemeToggle/>` here (see §2.B) | `grid place-items-center w-9 h-9 rounded-md border border-outline text-text-variant hover:text-text-main hover:border-primary` |
| Export btn | `border-outline-variant …hover:bg-surface-container-low hover:text-on-surface` (`:109-117`) | `border-outline …hover:bg-surface-low hover:text-text-main`; `text-text-variant` | add `title` (see copy) |
| Save btn | same family (`:118-125`) | same retoken; busy label retokened | |
| New-session btn | `bg-primary text-on-primary hover:bg-primary-container shadow-sm` (`:126-133`) | `bg-primary text-on-primary hover:bg-primary-dim` (drop heavy shadow; **no glow**) | |

### 2.B Theme toggle — **NEW** (`ThemeToggle.tsx` + `useTheme.ts`)

matrAIx is dark-first; toggling adds/removes the `light` class on
`document.documentElement` (the `:root.light` overrides live in §01). This is the
only behavior these new files add — pure presentation + a persisted preference.

- **`useTheme()` hook** (new, UI-only): state `'dark' | 'light'`; on mount read
  `localStorage['matraix-theme']`, else default **dark** (dark-first; optionally
  fall back to `matchMedia('(prefers-color-scheme: light)')` on first visit only);
  `toggle()` flips the value, writes localStorage, and
  `documentElement.classList.toggle('light', theme === 'light')`. Also set
  `documentElement.style.colorScheme` so native controls/scrollbars match.
- **`ThemeToggle` component** (new): a single icon button. Render `moon` when dark
  (click → light) / `sun` when light (click → dark). Classes per the header table.
  `aria-label` reflects the *next* state; `title="Toggle light / dark"`.
- **Mount:** in `TopBar`'s right cluster (`TopBar.tsx:104`). No other component
  needs to know the theme (everything is token-driven).

### 2.C Footer — **NEW** (`AppFooter.tsx`), slim + honest

There is no footer today (`App.tsx` is header → config bar → 3-pane grid). matrAIx
adds a slim status footer (mockup `app-redesign-v3.html:1279`). "Honest" = it shows
only real values already in scope — the active surface, the chatbot app, the
domain, and the *real* connection status read from the **existing** preflight query
cache (no new request, no fake metrics).

| Part | Target matrAIx | Source (honest, already in scope) |
|---|---|---|
| `<footer>` | `shrink-0 bg-surface-lowest border-t border-outline px-5 py-2` | — |
| Left context | `.hud text-[9px]`: `PersonaEval` `·` `chatbot · RecAI · {domain}` | surface label + `config.domain` (`App.tsx:309`) |
| Right status | dot + `.hud text-[9px]` label; mint `bg-secondary` + "Connected" when preflight `ready`, `bg-warn` + "Finishing setup" when `setup`, `bg-danger` + "Backend offline" when `offline`, pulsing `bg-warn` + "Checking…" while loading | reuse `useQuery(['preflight'])` from cache (same key as `PreflightChip.tsx:43`) — **read-only, no extra polling** |

Mount once in **both** shell branches of `App.tsx` (after the grid, and after the
cockpit/runs region) so it spans every surface.

### 2.D `App.tsx` wrapper edits (minimal)

| Location | Change |
|---|---|
| `App.tsx:386` (chat branch root) | keep `flex h-screen flex-col`; the 3-pane row already `min-h-0 flex-1` (`:402`) so it absorbs the footer; **add `<AppFooter .../>` after the grid** |
| `App.tsx:356` (persona-eval branch root) | same: add `<AppFooter/>` after `PersonaEvalCockpit`/`RunsView` |
| `App.tsx:413` centre `<main>` | `bg-background` → `bg-surface-dim` |
| `App.tsx:414-420` centre header | retoken: `bg-surface-container-lowest border-b border-border-soft` → `bg-surface-lowest border-b border-outline`; title `text-on-surface` → `font-semibold text-text-main`; `/ conversation` → see copy rewrite; `headerReq` chip `rounded-full border-border-soft bg-surface-container-low font-mono-sm text-on-surface-variant` → `.hud text-[9px] text-text-variant border border-outline rounded-full px-2.5 py-1` |
| `index.css` body | `background: var(--background)` → `--surface-dim`; default text → `--text-main` (token names per §01) |

Optional (not required for the reskin): nudge grid widths `280px / 1fr / 340px`
(`App.tsx:402`) toward the mockup's `256 / 1fr / 360`. Behavior identical; skip if
§01 prefers to leave metrics alone.

### 2.E Preflight chip + popover — `PreflightChip.tsx`

Keep all four tones and the polling query (`:43-48`). Retoken `TONE_CLASS`/`DOT_CLASS`
to the matrAIx semantic mapping and apply `.panel` to the popover.

| Element | Current | Target matrAIx |
|---|---|---|
| `ready` tone (`:26`) | `border-success/40 bg-success-container text-on-success-container` | `border-secondary/30 bg-secondary/10 text-secondary` |
| `setup`/`checking` (`:27,29`) | `…warning…` | `border-warn/30 bg-warn/10 text-warn` |
| `offline` (`:28`) | `…error…` | `border-danger/30 bg-danger/10 text-danger` |
| dots (`:32-37`) | `bg-success`/`bg-warning`/`bg-error` | `bg-secondary`/`bg-warn`/`bg-danger`; keep `animate-rb-pulse` on `checking` |
| popover (`:110-114`) | `rounded-lg border-border-soft bg-surface-container-lowest shadow-pop` | `panel rounded-md border-outline bg-surface-lowest shadow-2xl` |
| popover title (`:115`) | "Readiness checks", `uppercase tracking-wider text-on-surface-variant` | `.hud text-[10px] text-text-dim`; copy → "Setup checklist" |
| check rows (`:119-134`) | `Sym check_circle/error` `text-success/text-warning` | `text-secondary` (ok) / `text-warn` (todo); names/details unchanged (already user-facing) |

---

## 3. Chat workbench — session rail

### 3.A `SessionRail.tsx`

| Element | Current | Target matrAIx | Notes |
|---|---|---|---|
| `<aside>` (`:62`) | `border-r border-border-soft bg-surface-container-low` | `border-r border-outline bg-surface-lowest` | |
| Header (`:64-75`) | `Sessions` `text-headline-sm uppercase tracking-wider text-on-surface` + `add` button | `.hud text-[9px] text-text-dim`; consider matrAIx's full-width primary "New session" button at the rail top (`mockup:296`) **and** keep the compact `add` icon — either is fine; retoken add btn `border-outline-variant bg-surface-container-lowest hover:border-primary hover:text-primary` → `border-outline bg-surface-low hover:border-primary hover:text-primary` | |
| Active row (`:98-117`) | `bg-primary/10 text-on-surface`; `forum` icon `text-primary` | `border-l-2 border-primary bg-primary/5 text-text-main`; icon `text-primary` | matches mockup's left-accent active row |
| Idle row | `text-on-surface-variant hover:bg-surface-container` | `text-text-variant hover:bg-surface border-l-2 border-transparent` | |
| Title (`:111`) | `text-body-md` | `text-[13px]` (active `font-medium`) | |
| Sub-line (`:114`) | `subLine()` `text-label-md text-on-surface-variant` (e.g. `native · 4o-mini`) | `.hud text-[9px] text-text-dim` | keep the compose logic (`:22-29`); **add `title`** explaining the knobs (copy) |
| Turn count (`:116`) | `font-mono-sm tabular-nums text-on-surface-variant` | wrap into the sub-line as `… · {n} turns` (matches `mockup:300`) or keep as a `.hud` right chip | data unchanged |
| Skeleton (`:41-51`) | `bg-surface-container-high/-container` pulses | `bg-surface-high`/`bg-surface` pulses | keep `animate-rb-pulse` |
| Empty (`:85-88`) | "No sessions yet…" | retoken `text-text-variant`; copy rewrite below | |
| Footer nav (`:124-144`) | Catalog (+⌘K) / New session, `hover:bg-surface-container` | `hover:bg-surface`, `text-text-variant`, `.hud`/`text-[12px]`; `kbd` retoken like header | unchanged handlers |
| **Load-error state** | *(missing)* | **ADD** when `sessionsQuery.isError` (see §5) | needs a new `error?: boolean` + `onRetry?` prop, or read the query in the rail |

---

## 4. Chat workbench — conversation + composer + inspector

### 4.A Conversation thread — `ChatThread.tsx` + `ChatMessage.tsx`

The matrAIx target is the **bubble** thread (persona/you on the right, RecAI on the
left), mockup `:309-321`. This is a className + alignment-wrapper restyle of the
already-presentational `ChatMessage`; **its props and the parent's render loop
(`ChatThread.tsx:140-160`) do not change** — same `onClick` (focus turn), same
`onSelectItem`, same keyboard handler (`ChatMessage.tsx:96-100`), same `active`
highlight. (`ChatMessage`'s comment at `:5` says it deliberately avoided bubbles;
that comment should be updated to reflect the matrAIx bubble decision.)

| Element | Current (`ChatMessage.tsx`) | Target matrAIx |
|---|---|---|
| Row wrapper | full-width `px-lg py-2`; assistant is a focusable `role=button` `hover:bg-surface-container-low`, active `bg-primary/5` (`:90-112`) | column wrapper: user `flex flex-col items-end pl-10`; assistant `flex flex-col items-start pr-10`; keep assistant focusable wrapper + `title`; active → bubble gets `border-primary/60` |
| Name/label row (`:56-68`) | avatar circle + name + grey tag | replace with a `.hud text-[9px]` label above the bubble: user "You" (`text-text-dim`), assistant "RecAI" (`text-primary`, with bot icon). `avatar`/`name` props retained (feed `aria-label`/`title`) |
| User bubble body (`:69-75`) | inline text `text-on-surface-variant whitespace-pre-wrap` | `bg-surface border border-outline rounded-md rounded-tr-sm px-4 py-3 text-[13px] leading-relaxed text-text-main` |
| Assistant bubble body | inline `text-on-surface` (markdown) | `bg-surface border border-outline rounded-md rounded-tl-sm px-4 py-4 w-full text-[13px] leading-relaxed`; full width so the rec grid fits |
| Rec block (`:76-82`) | `flex flex-col gap-1.5` of `RecommendationCard` | inside the assistant bubble; divider `border-t border-outline pt-4` above; `grid grid-cols-1 sm:grid-cols-2 gap-3` |
| Tag → meta chips | grey `tag` text only | keep `tag` text as `.hud text-[8px] text-text-dim`; optional positive `bg-secondary/10 text-secondary` "Tool call OK" chip exists in mockup — only render facts we have (rec count / clarifying-question), no fake latency chip beyond `durationSeconds` |

`RecommendationCard.tsx` (lives inside the bubble):

| Element | Current (`:18-44`) | Target matrAIx |
|---|---|---|
| Card | `rounded-lg border-border-soft bg-surface-container-lowest hover:border-primary hover:bg-surface-container-low` | `rounded border-outline bg-surface-low p-3 hover:border-primary/60` (matches `mockup:315`) |
| Rank badge (`:27`) | `rounded-full bg-primary/10 text-primary` | `font-mono text-[10px] font-bold text-primary` (inline, no circle) |
| Title (`:31`) | `text-body-md text-on-surface` | `text-[12px] font-semibold text-text-main` |
| Meta (`:32`) | `text-body-sm text-on-surface-variant` | `text-[11px] leading-snug text-text-variant` |
| Score / id chip (`:35-40`) | `font-mono-sm … bg-surface-container` | `font-mono text-[10px] text-text-dim` / chip `bg-surface px-1.5` |
| "Best match" | *(none)* | optional `.hud text-[7px] text-secondary bg-secondary/10` corner ribbon **only on rank 1** (honest: derived from `rank`, `mockup:316`) |

`ChatThread` thread-level states:

| Element | Current | Target matrAIx |
|---|---|---|
| Scroll region (`:135`) | `custom-scrollbar pt-6` | keep; add `px-5 md:px-8 py-7`, inner `max-w-2xl mx-auto space-y-7` |
| EmptyThread (`:46-61`) | icon tile `bg-primary/10` + "Start the conversation" | retoken: tile `bg-surface-high border border-dashed border-outline`; headline `font-display font-semibold text-[15px]`; body `text-text-variant`; copy refresh below |
| ThinkingSkeleton (`:64-91`) | `bg-surface-container-high/-container` pulses + "warming/thinking" | retoken pulses → `bg-surface-high`/`bg-surface`; label `.hud text-[9px] text-primary`; spinner → `loader-2 animate-spin text-primary` (mockup `:599`); keep `building` vs `running` copy (refreshed below) |
| Error row (`:173-197`) | `rounded-lg border-error/40 bg-error-container/40` + `Sym error text-error` + Retry `bg-primary` | `panel rounded-md border border-danger/40 border-l-4 border-l-danger bg-danger/10`; icon tile `bg-danger/10 border-danger/30 text-danger alert-triangle`; Retry → `border-danger/40 bg-danger/10 text-danger hover:bg-danger/20` (mockup `:678`); copy refresh below |

### 4.B Composer — `Composer.tsx` (the `>_` composer)

Keep the auto-growing `<textarea>`, the ⌘↵-to-send behavior (`:49-55`), the
`isPending`/`blocked` logic, and `onSend`. Restyle to the matrAIx terminal-style
field: a mono `>_` prompt prefix, `bg-field` frame, primary send button on the
right. Keep the cold-start hint, demoted to a slim helper line **below** the field.

| Element | Current | Target matrAIx |
|---|---|---|
| Bar (`:58`) | `border-t border-border-soft bg-surface-container-lowest` | `border-t border-outline bg-surface-lowest`; inner `max-w-2xl mx-auto` |
| Field frame (`:59`) | `rounded-xl border-outline-variant bg-surface-container-lowest focus-within:border-primary focus-within:shadow-[…primary-tint]` | `flex items-stretch rounded-md border border-outline bg-field focus-within:border-primary` |
| **`>_` prefix** | *(none)* | **ADD** leading `<span class="self-start pl-3.5 pt-3 text-primary font-mono font-bold">&gt;_</span>` (mockup `:323`) |
| Textarea (`:60-70`) | `bg-transparent text-on-surface placeholder:text-outline` | `bg-transparent text-text-main placeholder:text-text-dim font-mono text-[13px]`; keep `rows`, `MAX_TEXTAREA_HEIGHT`, auto-size |
| Send button (`:80-92`) | `h-8 w-8 rounded-md bg-primary hover:bg-primary-container`; `autorenew` spin / `arrow_forward` | `self-stretch px-5 rounded-r-md bg-primary text-on-primary hover:bg-primary-dim`; busy `loader-2 animate-spin` / idle `arrow-up` (no glow) |
| Hint (`:71-79`) | inline left of send: "first turn warms the recommender (~min) · then fast" / pending variants | move **below** field as `.hud text-[8px] text-text-dim mt-2` helper; copy refreshed below |
| **Offline hint** | always `disabled={false}` (`App.tsx:434`) | **ADD (optional, honest):** when preflight is `offline`, show the helper "Start the backend to send a message" and keep send disabled; otherwise unchanged. UI-only — reads the cached preflight query |

### 4.C Turn inspector — `TurnInspector.tsx` (Trace / Output / Scores **tabs**)

matrAIx restructures the inspector from three stacked sections into a **tabbed**
pane (mockup `:326-335`). The three real sections map cleanly onto the tab labels;
no `TurnView` field is added or faked.

- **Trace** ← the existing Tool-plan timeline (`:223-239`, BufferStore → HardFilter
  → Rank → Map).
- **Output** ← the existing Recommended-items list (`:242-258`) **+** the
  collapsible raw native-action block (`NativeRaw`, `:103-145`).
- **Scores** ← **honest teaching panel.** A manual chat turn is not scored by a
  PersonaEval scorer, and `TurnView` has no score fields — so this tab surfaces the
  real per-turn signals we *do* have (latency `durationSeconds`, recommendation
  count, whether RecAI asked a clarifying question) and explains that full scores
  (Overall 0–10, Constraint /5, Preference /5) come from running this in
  **PersonaEval**, with a link to that surface. This respects the "never invent
  data" rule and matches the chatbot scoring truth without fabricating it.

Tab state is **new local UI state** (`useState<'trace'|'output'|'scores'>('trace')`)
— the only addition; the data plumbing (`turns`, `activeIndex`, `onSelectIndex`,
`:181`) is unchanged.

| Element | Current | Target matrAIx |
|---|---|---|
| `<aside>` (`:189`) | `border-l border-border-soft bg-surface-container-lowest` | `border-l border-outline bg-surface-lowest` |
| Header (`:191-214`) | `manage_search` + "Turn inspector" `text-headline-sm uppercase` + turn `<select>` | `flex justify-between px-4 py-3 border-b border-outline bg-surface`; title `.hud text-[10px] text-primary`; right `.hud text-[9px] text-text-dim "turn N"`; keep the `<select>` turn picker (retoken `border-outline bg-surface-low`) for jump-to-turn |
| **Tab strip** | *(none — stacked sections)* | **ADD** `flex gap-5 px-4 border-b border-outline text-[12px]`; each tab `border-b-2 -mb-px py-2.5`; active `border-primary text-primary`, idle `border-transparent text-text-dim hover:text-text-variant` (mockup `:327`) |
| Section labels (`SectionHeader :42-48`) | `uppercase tracking-wider text-on-surface-variant` + mono count | `.hud text-[9px] text-text-dim` + `font-mono text-[11px]` count |
| Plan node (`PlanStepRow :52-84`) | ok `border-success bg-success-container`; pending `border-outline-variant bg-surface-container`; error `border-error bg-error-container`; connector `bg-border-soft` | ok `border-secondary/40 bg-secondary/10 text-secondary`; pending `border-outline bg-surface text-text-dim`; error `border-danger/40 bg-danger/10 text-danger`; connector `bg-outline`; tool name `text-text-main`, detail `font-mono text-[11px] text-text-variant`; Trace can also adopt the mockup's numbered mono list (`:329`) — both are faithful to `PlanStep` |
| Rec item row (`RecItemRow :88-100`) | `panel`-less `rounded-md border-border-soft bg-surface-container-lowest`; score `text-primary` | `rounded border-outline bg-surface-low`; rank/id `font-mono text-[11px] text-text-dim`; score `font-mono text-[11px] font-semibold text-primary` |
| NativeRaw (`:103-145`) | toggle `bg-surface-container-low hover:bg-surface-variant`; `<pre>` `bg-surface text-on-surface-variant`; `# raw_tool_outputs` | toggle `bg-surface-low hover:bg-surface-high border-outline`; `<pre>` `panel bg-surface font-mono text-[10.5px] text-text-variant`; add a copy button (mockup `:330`); comment label retokened `text-text-dim` |
| Empty (`InspectorEmpty :157-171`) | tile `bg-surface-container` + body | tile `bg-surface-high border-outline`; `text-text-variant`; copy refresh below |
| **Scores tab body** | *(new)* | small `.hud`-labeled stat cards (`bg-surface border-outline rounded-md p-4 font-display text-[20px]`) for the honest per-turn signals + a `text-[12px] text-text-variant` teaching note + a `text-primary` link "Score this persona in PersonaEval →" (switches surface via the existing nav) |

---

## 5. Missing UI states to ADD (UI-only)

| State | Where | Behavior |
|---|---|---|
| **Sessions list failed to load** | `SessionRail` (currently only loading/empty/list, `:78-121`) | when `sessionsQuery.isError`: a quiet card — `alert-triangle text-warn`, "Couldn't load your chats", `Recheck` button calling `sessionsQuery.refetch()`. Pass `isError`/`onRetry` into the rail (new props) |
| **Active session failed to load** | centre `<main>` (`App.tsx:413`) — today a failed `getSession` shows nothing | render a centered error card (same family as the thread error) with "Couldn't open this chat" + Retry; gate on `sessionQuery.isError` |
| **Backend offline → composer** | `Composer` (§4.B) | disable send + show "Start the backend to send a message" helper when preflight `offline` |
| **Scores on a manual turn** | inspector Scores tab (§4.C) | honest teaching panel, never a fake score |
| **First-run tutorial** | EmptyThread + empty SessionRail | one-time inline guidance (copy below) so a first-time user knows they play the user and RecAI replies |

All read existing queries/caches; none adds a request, mutation, or type.

---

## 6. Copy rewrites

All user-facing strings rewritten to be friendly and tutorial-like for a
first-time user, while staying restrained/professional. HUD micro-labels stay
real words.

### 6.1 Rewrites

| Location | Current text | Friendly rewrite |
|---|---|---|
| Header wordmark (`TopBar.tsx:65`) | `PersonaEval` | `matrAIx` (with `AI` in primary) — product brand; "PersonaEval" stays as the nav surface + footer |
| Search btn (`TopBar.tsx:74`) | "Search catalog" | "Search personas & items" |
| Search aria (`TopBar.tsx:70`) | "Search the catalog (⌘K)" | "Search the catalog of personas and items — press Command-K" |
| Export btn (`TopBar.tsx:116`) | "Export" | keep label; **add** `title`: "Download this chat as a file" |
| Save btn (`TopBar.tsx:124`) | "Save" / "Saving…" | keep; **add** `title`: "Save this chat to the server" |
| New-session btn (`TopBar.tsx:132`) | "New session" | "New chat" (consistent with "chats" everywhere) |
| Centre header (`App.tsx:416`) | "/ conversation" | "· manual chat" + `title`: "You type as the user; RecAI replies. No persona is simulated here." |
| Centre status: building/running/timeout (`App.tsx:326-331`) | "warming…" / "running…" / "timed out" | "Warming up…" / "Working…" / "Timed out" |
| Centre status: counts | "no turns yet" / "{n} turns" | "No messages yet" / "{n} turns" (term taught in empty state) |
| Assistant name (`ChatThread.tsx:151`, `ChatMessage`) | "RecBot" | "RecAI" + first-use tooltip: "RecAI — the recommender app you're testing" |
| Assistant tag (`ChatThread.tsx:37-43`) | "· turn N · M recommendations" / "· asked a clarifying question" | "Turn N · recommended M items" / "Turn N · asked you a question" |
| User name/tag (`ChatThread.tsx:143`) | "You" · "· turn N" | "You" · "Turn N" (you're playing the user) |
| Empty thread (`ChatThread.tsx:53-57`) | "Start the conversation" / "Reply as the user below to send the first turn. The first message warms the recommender (about a minute); after that, turns run fast." | "Start the conversation" / "You'll play the user here — type what they'd want and RecAI will recommend. Heads up: the first message wakes the recommender (about a minute); after that, replies are quick." |
| Thinking skeleton (`ChatThread.tsx:76-87`) | "warming the recommender…" / "thinking…" + "Cold start — loading the catalog and resources. This first turn can take a minute." / "Planning tools and ranking candidates from the catalog…" | "Waking the recommender…" / "Thinking…" + "First message — RecAI is loading its catalog and tools. This one turn can take a minute." / "Choosing the right tools and ranking items for you…" |
| Thread error (`ChatThread.tsx:179-180`) | "This turn didn't finish" / {error} | "That message didn't go through" / keep {error}; Retry stays |
| Composer placeholder (`Composer.tsx:67`) | "Reply as the user…  ⌘↵ to send" | "Type a message as the user you're playing — press ⌘↵ to send" |
| Composer hint idle (`Composer.tsx:78`) | "first turn warms the recommender (~min) · then fast" | "The first message wakes the recommender (about a minute), then replies are quick" |
| Composer hint building/running (`:75-77`) | "warming the recommender — first turn takes ~a minute" / "running the turn…" | "Waking the recommender — the first message takes about a minute" / "Sending your message…" |
| Composer aria (`:68,84`) | "Message the recommender" / "Send message" | "Type a message to RecAI" / "Send message" |
| Rail header (`SessionRail.tsx:65`) | "Sessions" | "Your chats" |
| Rail new-session aria/title (`:69-70`) | "New session" | "Start a new chat" |
| Rail sub-line (`:114`) | e.g. "native · 4o-mini" | keep compact; **add** `title`: "Ranker: native · Model: gpt-4o-mini — change these in the bar above" |
| Rail empty (`:86-87`) | "No sessions yet. Create one to start a conversation with the recommender." | "No chats yet. Start one to try the recommender — you'll play the user and RecAI replies." |
| Untitled (`:112`) | "Untitled session" | "Untitled chat" |
| Rail footer (`:131,142`) | "Catalog" / "New session" | "Browse catalog" / "New chat" |
| Inspector title (`TurnInspector.tsx:193`) | "Turn inspector" | "Turn inspector" (keep; it's a clear HUD label) |
| Inspector tabs | *(new)* | "Trace" · "Output" · "Scores" |
| Trace section (`:225`) | "Tool plan" / "{n} steps · all ok" | "What RecAI did" / "{n} steps · all OK" |
| Trace empty (`:236`) | "No structured tool plan was emitted for this turn." | "No tool steps were recorded for this turn." |
| Output recs (`:244`) | "Recommended items" / "{n} · mapped" | "Items it recommended" / "{n} items" |
| Output recs empty (`:255`) | "This turn returned no recommendations (e.g. a clarifying question)." | "RecAI asked you a question this turn instead of recommending." |
| Output raw (`NativeRaw :112,124,108`) | "Native action · raw" / "native_action.raw" / "(no native action emitted)" | "RecAI's raw output" / "raw model action" / "RecAI didn't emit a raw action for this turn." |
| Raw outputs comment (`:135`) | "# raw_tool_outputs" | "# tool outputs" |
| Inspector empty (`:164-166`) | "Select an assistant turn to inspect its tool plan, ranked candidates, and the raw model action." | "Click any RecAI reply to see how it answered — the tools it ran, the items it picked, and its raw output." |
| Preflight offline (`PreflightChip.tsx:78`) | "API offline" / "Start the API to run turns" | "Backend offline" / "Start the PersonaEval backend to send messages" |
| Preflight setup (`:85-87`) | "Setup needed" / "{n} items need attention" | "Almost ready" / "{n} thing{s} left to finish" |
| Preflight ready/checking (`:75,82`) | "Checking…" / "Ready" | keep "Checking…" / "Ready" |
| Preflight popover title (`:116`) | "Readiness checks" | "Setup checklist" |
| Footer status | mockup "connected" | "Connected" / "Finishing setup" / "Backend offline" / "Checking…" (mirrors preflight) |

### 6.2 New helper text, empty states, tooltips & first-run hints (ADD)

- **Theme toggle** — `aria-label` "Switch to light theme" (when dark) /
  "Switch to dark theme" (when light); `title` "Toggle light / dark".
- **Footer** — `aria-label` on the status region: "Backend connection status".
  Left context reads exactly "PersonaEval · chatbot · RecAI · {domain}" (real values).
- **First-run hint (empty rail + empty thread):** a single dismissible line —
  "New to PersonaEval? In Chat you role-play a user and RecAI recommends. When you
  want automated scoring, switch to the PersonaEval tab."
- **"RecAI" first-use tooltip:** "RecAI is the recommendation app you're testing.
  It runs tools, then suggests items."
- **Inspector Scores tab — teaching note (honest):** "This is a manual chat, so it
  isn't scored. What we can show: it replied in {latency}, recommended {n} items{,
  and asked a clarifying question}. For Overall / Constraint / Preference scores,
  run this persona in PersonaEval." + link "Score in PersonaEval →".
- **Composer offline helper:** "The backend is offline — start it to send a message."
- **Sessions-load-error card:** "Couldn't load your chats. The backend may be
  starting up." + "Recheck" button.
- **Active-session-load-error card:** "Couldn't open this chat — it may have been
  removed, or the backend is offline." + "Retry" button.
- **Tooltips:** Export → "Download this chat as a file"; Save → "Save this chat to
  the server"; rail sub-line → "Ranker: {rankerMode} · Model: {engine} — change in
  the bar above"; centre "manual chat" → "You type as the user; RecAI replies. No
  persona is simulated here."


---

# 03 · PersonaEval cockpit — chatbot (config · environment · pipeline · feed · inspector)

## Scope & approach

This section reskins the **chatbot** cockpit only (`ChatbotEvalCockpit` in
`PersonaEvalCockpit.tsx:140-456`). Survey/Web have their own cockpits and their own
section. Everything here is a **pure in-place reskin**: the three-column layout, the
state, the `usePersonaEval` wiring, the keyboard shortcuts (`PersonaEvalCockpit.tsx:331-373`),
the export logic, and every component's props/structure stay exactly as they are. We
only (a) swap design tokens, (b) restyle JSX `className`s to the matrAIx language,
(c) add the missing first-run/teaching states + the launch hint, and (d) rewrite copy.

The matrAIx mockup splits "configure" and "chat" into two screens; **we do not
re-architect**. The existing combined cockpit (config bar on top → pipeline → live
trajectory → inspector on the right) is kept; we map the mockup's *visual language*
(panels, `.hud` micro-labels, `.panel` corner bracket, app cards, env rows, pipeline
nodes, bubbles, scorecard bars, the single `.glow` CTA) onto the existing components.

One thing the design system mandates that this cockpit currently violates: the
**icon set**. Every cockpit element draws Material Symbols via the `Sym` wrapper
(`cockpitShared.tsx:55-67`); matrAIx is lucide. To preserve all call sites
(structure), re-point the `Sym` wrapper at `lucide-react` and add a name map — the
~30 glyphs this cockpit uses are mapped in the *Icon map* table below. The
font-loading / library decision is owned by the design-system + shell sections; this
section just lists the chatbot glyphs.

---

## Shared token translation (applies to every table below)

The cockpit is currently styled in the old "Executive Precision" Material-3-ish token
set. Map it to matrAIx wholesale; the per-component tables only call out deviations.

| role | current token(s) | matrAIx target | notes |
|---|---|---|---|
| page background | `bg-background` | `bg-surface-dim` | the `<main>` (`PersonaEvalCockpit.tsx:384`) |
| panel / card body | `bg-surface` | `bg-surface` + `.panel` on headline panels | `.panel` adds the cyan corner bracket |
| inset / header / sub-card | `bg-surface-container-lowest` | `bg-surface-lowest` | headers, popover, bubbles, scorecard |
| recessed row / sub-panel | `bg-surface-container-low` | `bg-surface-low` | |
| chip / active menu row | `bg-surface-container` | `bg-surface-high` | mono id chips, hover rows |
| raised fill | `bg-surface-container-high` / `-highest` | `bg-surface-high` | |
| input surface | (KnobSelect button `bg-surface`) | `bg-field` | knobs read as fields now |
| hairline border | `border-border-soft` | `border-outline-dim` | |
| structural border | `border-outline-variant` | `border-outline` | |
| primary CTA | `bg-primary text-on-primary` | `bg-primary text-on-primary` + `.glow` (Run only) | |
| primary hover | `hover:bg-primary-container` | `hover:bg-primary-dim` | |
| accent text/icon | `text-primary` | `text-primary` | cyan |
| accent tint | `bg-primary/5` · `bg-primary/10` | `bg-primary/10` | |
| body text | `text-on-surface` | `text-text-main` | |
| secondary text | `text-on-surface-variant` | `text-text-variant` | |
| muted / micro text | `text-on-surface-variant` (in `.hud` spots) · `text-outline` | `text-text-dim` | |
| heading font | `text-display`/`text-headline-* font-display`/`font-headline-*` | `font-display` (Space Grotesk) + size util | keep sizes |
| HUD micro-label | `text-label-md font-label-md uppercase tracking-wider` | `.hud` | mono uppercase tracked |
| mono data | `font-mono-sm text-mono-sm` | `font-mono text-[11px]` (JetBrains Mono) | |
| focus ring | `FOCUS_RING` w/ `ring-offset-surface-container-lowest` (`cockpitShared.tsx:30-31`) | same, offset → `ring-offset-surface-lowest` | one-line change |

**Semantic colors (status + scores).** The cockpit's red→amber→green ramp maps to
matrAIx mint/warn/danger. This is the single source of truth `SCORE_BAND_CLASS`
(`cockpitShared.tsx:329-334`); `scoreBand()` logic is unchanged:

| band | current | matrAIx target |
|---|---|---|
| high / success / pass | `text-on-success-container` · `bg-success` · `bg-success-container` | `text-secondary` · `bg-secondary` · `bg-secondary/15` |
| mid / warning | `text-on-warning-container` · `bg-warning` · `bg-warning-container` | `text-warn` · `bg-warn` · `bg-warn/15` |
| low / error | `text-on-error-container` · `bg-error` · `bg-error-container` | `text-danger` · `bg-danger` · `bg-danger/15` |
| none / idle | `text-on-surface-variant` · `bg-outline-variant` · `bg-surface-container-high` | `text-text-dim` · `bg-outline` · `bg-surface-high` |

> Note: the mockup paints the *Preference* bar cyan (`text-primary`) decoratively. We
> do **not** — primary/cyan never encodes a score. Color always means pass/mid/fail
> (mint/warn/danger), matching the matrAIx semantic contract.

**Icon map (Material Symbol → lucide) for this cockpit's `Sym` call sites:**
`forum→message-square` · `fact_check→clipboard-check` · `language→globe` ·
`history→history` · `download→download` · `play_arrow→play` · `autorenew→loader`
(spin) · `expand_more/less→chevron-down/up` · `check→check` · `hub→server-cog` ·
`lock→lock` · `storage→database` · `account_tree→git-fork` · `badge→scan-face` ·
`smart_toy→brain-circuit` · `face→scan-face` · `info→info` · `more_horiz→more-horizontal`
· `error→alert-triangle` · `refresh→refresh-cw` · `flag→flag` · `play_circle→circle-play`
· `groups→users` · `code→braces` · `bolt→zap` · `filter_alt→filter-alt` ·
`leaderboard→bar-chart-3` · `database→database` · `map→map` · `timer→timer` ·
`verified→shield-check` · `help/help_outline→circle-help` · `check_circle→check-circle`
· `cancel→x-circle` · `remove_circle→minus-circle` · `movie→clapperboard` ·
`stadia_controller→gamepad-2` · `self_care→sparkles` · `terminal→terminal` ·
`data_object→braces` · `person/person_search→user/user-search`.

---

## A. Application-type switch — `TaskTypeSwitch.tsx`

Segmented control (Chatbot / Survey / Web). Structure (`OPTIONS` map, buttons) kept.

| element | current | target | notes |
|---|---|---|---|
| bar | `border-b border-border-soft bg-surface px-lg py-2` (`:19`) | `border-b border-outline-dim bg-surface-lowest px-5 py-2.5` | sits in the inset header band |
| label "Application type" | `text-label-md … uppercase tracking-wider text-on-surface-variant` (`:20`) | `.hud text-text-dim` | |
| segment group | `rounded-md border border-border-soft bg-surface-container-low` (`:23`) | `rounded-md border border-outline bg-surface-low p-1 inline-flex` | matches mockup `:107` |
| selected segment | `bg-primary text-on-primary` (`:34`) | `bg-primary text-on-primary rounded` | |
| idle segment | `text-on-surface-variant hover:bg-surface-container hover:text-on-surface` (`:35`) | `text-text-variant hover:bg-surface hover:text-text-main` | |
| icon fill on select | `fill={selected?1:0}` (`:38`) | lucide has no fill axis — drop `fill`, keep `text-primary` tint when selected | |

---

## B. Run header — `RunHeader.tsx`

Persona identity (left) + Runs / Export / Run actions (right). Structure kept; **add
the launch hint** (a new line; the mockup carries it under the CTA, `:287`).

| element | current | target | notes |
|---|---|---|---|
| header bar | `border-b border-border-soft bg-surface-container-lowest px-lg py-sm` (`:49`) | `border-b border-outline-dim bg-surface-lowest px-5 py-sm` | |
| persona title `<h1>` | `text-display font-display text-on-surface` (`:51`) | `font-display text-[20px] font-bold tracking-tight text-text-main` | Space Grotesk |
| codename chip | `bg-surface-container … font-mono-sm text-on-surface-variant` (`:53`) | `bg-surface-high font-mono text-[11px] text-text-dim rounded px-2 py-1` | |
| (add) source chip | — | `.hud text-[9px] text-secondary border border-secondary/30 bg-secondary/10 rounded px-1.5 py-0.5` | optional, mirrors mockup `:239` (e.g. "Nemotron") |
| Runs button | `text-on-surface-variant hover:bg-surface-container-low hover:text-primary` (`:63`) | `text-text-variant hover:bg-surface hover:text-primary` | |
| Export button | `border border-outline-variant text-on-surface-variant hover:bg-surface-container-low` (`:72`) | `border border-outline bg-surface-low text-text-variant hover:border-primary hover:text-text-main` | |
| **Run / Re-run CTA** | `bg-primary px-4 py-2 text-on-primary shadow-sm hover:bg-primary-container` (`:81`) | `glow bg-primary text-on-primary rounded-md hover:bg-primary-dim` + `font-display font-semibold` | **the single `.glow`** in the cockpit |
| busy spinner | `Sym autorenew animate-rb-spin` (`:84`) | lucide `loader` + `animate-rb-spin` | |
| **(add) launch hint** | — | `<p class="text-center text-[11px] text-text-dim leading-relaxed">` directly under/after the CTA | copy below; teaches what "Run" does |

States: CTA disabled (`!persona`) → `disabled:opacity-55`; running → "Running…" +
spinner; terminal → "Re-run eval". Keep all.

---

## C. Application picker (RecAI / OpenBB / Medical)

**Today** this is a `KnobSelect` dropdown labelled "Application" inside `RunConfigBar`
(`RunConfigBar.tsx:101-109`). The approved matrAIx design (`:148-168`) elevates it to a
**3-card picker** — and the app choice is the most consequential, app-shape-defining
knob, so it deserves the cards.

Two paths, pick per effort budget:

- **Baseline (zero structure change):** restyle the existing "Application" `KnobSelect`
  per *Table D / KnobSelect* below. Ships immediately.
- **Recommended (presentational add):** a new `ApplicationPicker` sub-component that
  renders `applicationOptions` (`RunConfigBar.tsx:89`) as cards and calls the **same**
  `onApplicationId`. No data/logic change — `label` + `description` come straight from
  the knob metadata; only the per-app icon is a presentational constant (same pattern
  as `DOMAIN_META`, `RecommendedItems.tsx:16-20`).

| card element | target classes | notes |
|---|---|---|
| panel wrapper | `.panel bg-surface border border-outline rounded-md p-5` | header row: `.hud text-text-dim "Application"` + `.hud text-text-dim "{n} adapters"` |
| card | `apppick rounded-md border border-outline bg-surface-low p-3.5 hover:border-primary` | active → `border-primary bg-primary/10` + a `check` glyph top-right |
| icon tile | `w-9 h-9 grid place-items-center rounded bg-surface-high border border-outline` | icon `text-primary` (active/RecAI) else `text-text-variant` |
| title | `font-semibold text-[13px] text-text-main` | from `option.label` |
| tagline | `text-text-dim text-[11px] leading-snug` | from `option.description` |

Per-app icons (presentational map): `recai→clapperboard`, `finance_openbb→line-chart`,
`medical_assistant→stethoscope` (matches mockup `:154-165`).

---

## D. Run-config knobs — `RunConfigBar.tsx` + `KnobSelect.tsx`

Knobs rendered: Application model (`engine`), Persona model, **Domain (RecAI-only**,
already gated `RunConfigBar.tsx:91,128`), Conversation style (the accent knob), Max-turns
slider. Keep the custom `KnobSelect` (button + listbox) — it exists to show each
option's `description`, which a native `<select>` can't; that's a feature to preserve.

### RunConfigBar shell

| element | current | target | notes |
|---|---|---|---|
| bar | `border-b border-border-soft bg-surface-container-lowest px-lg py-2.5 shadow-sm` (`:100`) | wrap as a `.panel bg-surface border border-outline rounded-md` titled `.hud text-primary "Run configuration"` (mockup `:170-184`) — or keep the flat bar with matrAIx tokens if vertical space is tight | the panel framing reads more "configure"; the flat bar is the lower-risk reskin |
| knob label | `text-label-md … uppercase tracking-wider text-on-surface-variant` (`KnobSelect.tsx:101`) | `.hud text-text-dim block mb-1.5` | |
| Domain label suffix | (none) | append `<span class="text-primary normal-case tracking-normal">· RecAI</span>` | teaches *why* it appears/disappears (mockup `:177`) |
| slider label | `text-label-md … text-on-surface-variant` + value chip `bg-surface-container font-mono-sm` (`:152-158`) | `.hud text-text-dim` + value `font-mono text-text-variant` | |
| slider | `bg-outline-variant accent-primary` (`:168`) | `bg-outline accent-primary` | |

### KnobSelect (the dropdown itself)

| element | current | target | notes |
|---|---|---|---|
| trigger (default) | `border-outline-variant bg-surface text-on-surface hover:border-primary` (`:114`) | `border-outline bg-field text-text-main hover:border-primary` | reads as a field |
| trigger (accent — Conversation style) | `border-primary bg-primary/5 text-primary hover:bg-primary/10` (`:113`) | `border-primary bg-primary/10 text-primary hover:bg-primary/15` | keep the highlighted knob |
| chevron | `Sym expand_more text-outline` (`:118`) | lucide `chevron-down text-text-dim` | |
| menu | `border-border-soft bg-surface-container-lowest shadow-pop` (`:129`) | `border-outline bg-surface-lowest rounded-md shadow-pop custom-scrollbar` | |
| active row | `bg-surface-container` (`:142`) | `bg-surface-high` | |
| selected label | `text-primary` + `Sym check` (`:146-149`) | `text-primary` + lucide `check` | |
| option description | `text-[11px] text-on-surface-variant` (`:152`) | `text-[11px] text-text-dim leading-relaxed` | **keep** — this is the teaching surface |

---

## E. Read-only Harbor environment — `EnvironmentPopover.tsx`

Per-option truth: **only chatbot shows this** (already true — it lives in the chatbot-only
`RunConfigBar`). The mockup makes it a persistent right-rail panel; our right rail is the
Inspector, so **keep it as the popover** (structure) and restyle to read as a fixed
"facts" surface. Rows already map to matrAIx labels: Selection=`ranker`, Agent=`agent`,
Resources=`resources` (`EnvironmentPopover.tsx:56-60`).

| element | current | target | notes |
|---|---|---|---|
| trigger button | `bg-surface-container-low text-on-surface-variant hover:bg-surface-container` (`:77`) | `bg-surface-low border border-outline text-text-variant hover:border-primary` + lucide `server-cog` | |
| popover panel | `border-border-soft bg-surface-container-lowest shadow-pop` (`:89`) | `.panel bg-surface-lowest border border-outline rounded-md shadow-pop` | |
| section headers ("Harbor environment" / "Application stack" / "Prompt boundary") | `text-[11px] … uppercase tracking-wider text-on-surface-variant` (`:91,106,122`) | `.hud text-text-dim` | |
| **(add) Read-only chip** | — | `.hud text-[8px] text-text-dim border border-outline rounded px-1.5 py-0.5 "Read-only"` next to the header | mockup `:251`; signals "fixed by the sandbox" |
| row label | `text-body-sm text-on-surface-variant` (`:98`) | `.hud text-[9px] text-text-dim` | |
| row value (mono chip) | `bg-surface-container font-mono-sm text-on-surface` (`:99`) | `font-mono text-[11px] text-text-variant` (drop the chip bg; matrAIx shows bare mono) | |
| prompt-boundary values | `text-body-sm font-medium text-on-surface` (`:130`) | `text-[11px] text-text-dim leading-relaxed` | |

**Per-app Selection / Agent / Resources.** matrAIx requires these three to differ by
app (RecAI vs OpenBB vs Medical). The data layer exposes a single `ConfigEnvironment`
(`types.ts:89-100`), so these are *fixed infrastructure facts*, not run data — i.e. a
presentational constant in the same spirit as `DOMAIN_META` / the mockup's `appEnv`
(`app-redesign-v3.html:1330-1334`). Add an `APP_ENVIRONMENT` display map keyed by
`applicationId`, falling back to the `environment` block when a field is absent (never
fabricate). Values per the approved design:

| app | Selection | Agent | Resources |
|---|---|---|---|
| `recai` | SASRec ranker | InteRecAgent | recai_resources |
| `finance_openbb` | Finance tool selection | OpenBB research agent | OpenBB data providers |
| `medical_assistant` | Clinical retrieval | Medical assistant agent | Medical knowledge base |

This requires passing `applicationId` into `EnvironmentPopover` (one new prop, no logic
change). Runtime/Chatbot API/Scorer/Cache stay sourced from `environment`.

---

## F. Component pipeline — `ComponentPipeline.tsx`

Persona → Chatbot → Scorer, each a status card with tone idle/active/done/error
(`:76-81`). Keep the node cards + arrows + the existing status state machine
(`personaStatus`/`chatbotStatus`/`scorerStatus`, `:30-74`).

| element | current | target | notes |
|---|---|---|---|
| section | `border-b border-border-soft bg-surface-container-lowest px-lg py-2.5` (`:129`) | `border-b border-outline-dim bg-surface-lowest px-5 py-2.5` | optional: title row `.hud text-text-dim "Pipeline"` (mockup `:117`) |
| node card | `border-border-soft bg-surface-container-low px-3 py-2` (`:134`) | `border-outline bg-surface-low rounded-md px-3 py-2` | |
| node label | `text-label-md … uppercase tracking-wider text-on-surface` (`:140`) | `.hud text-text-main` | |
| owner (mono) | `font-mono-sm text-on-surface` (`:145`) | `font-mono text-[11px] text-text-variant` | |
| detail | `text-body-sm text-on-surface-variant` (`:146`) | `text-[12px] text-text-dim leading-snug` | **rewrite the Scorer detail** (copy table) |
| arrow connector | `Sym arrow_forward text-outline` (`:150`) | lucide `chevron-right text-text-dim` | |
| **tone: active** | `border-primary/35 bg-primary-container/45 text-primary` (`:77`) | `border-primary/40 bg-primary/10 text-primary` | |
| **tone: done** | `border-success/30 bg-success-container/55 text-on-success-container` (`:78`) | `border-secondary/40 bg-secondary/10 text-secondary` | mint |
| **tone: error** | `border-error/30 bg-error-container/55 text-on-error-container` (`:79`) | `border-danger/40 bg-danger/10 text-danger` | |
| **tone: idle** | `border-border-soft bg-surface-container text-on-surface-variant` (`:80`) | `border-outline-dim bg-surface-low text-text-dim` | |

The status-chip pill (`:141`) reuses the same `toneClass`, so it inherits the mapping.

---

## G. Trajectory feed — `Trajectory.tsx`, `TurnBubble.tsx`, `RecommendedItems.tsx`, `ToolPlanFold.tsx`

### Trajectory container & states

| element | current | target | notes |
|---|---|---|---|
| scroll container | `custom-scrollbar … bg`(inherits) `p-lg` (`:104`) | keep `custom-scrollbar`, page sits on `bg-surface-dim` | |
| scenario banner | `border-border-soft bg-surface-container-lowest shadow-soft` + `Sym info text-primary` (`:107-117`) | `.panel? no` → `border border-outline bg-surface-lowest rounded-md` + lucide `info text-primary`; heading `font-display` | keep "Scenario · {style}" |
| focused-turn ring | `bg-primary/5 ring-1 ring-primary/20` (`:129`) | `bg-primary/5 ring-1 ring-primary/30` | J/K focus |
| **empty (no persona)** `:86-101` | icon tile `bg-primary/10` + `Sym groups`; `text-headline-md font-headline-md`; body `text-on-surface-variant` | tile `bg-primary/10` + lucide `users text-primary`; heading `font-display text-text-main`; body `text-text-variant` | copy rewrite below |
| **empty (ready)** `:193-204` | tile `bg-surface-container` + `Sym play_circle`; `kbd` chip `bg-surface-container` | tile `bg-surface-high` + lucide `circle-play text-text-dim`; `kbd` → `bg-surface-high border-outline-dim font-mono` | |
| **warming/running skeleton** `:145-147,211-233` | `animate-rb-pulse bg-surface-container/-high` shimmer + `Sym autorenew animate-rb-spin text-primary` | same shimmer on `bg-surface-high`; spinner → lucide `loader text-primary` | label copy below |
| **thinking line** `:150-155` | `Sym more_horiz animate-rb-pulse` + `text-on-surface-variant` | lucide `more-horizontal animate-rb-pulse text-text-dim` | live status copy below |
| **failed** `:158-178` | `border-error/40 bg-error-container/40` + `Sym error text-error`; Retry `bg-primary hover:bg-primary-container` | `border-danger/40 bg-danger/10` + lucide `alert-triangle text-danger`; Retry `bg-primary hover:bg-primary-dim` | preserves config |
| **run complete** `:181-190` | divider + `Sym flag text-on-success-container` "Run complete" | divider `border-outline-dim` + lucide `flag text-secondary` + `.hud text-secondary` | mint |

### TurnBubble

matrAIx keeps both bubbles on bordered surfaces, distinguished by alignment + a `.hud`
speaker label + corner radius (mockup `:310-320`). Drop the filled-indigo persona bubble.

| element | current | target | notes |
|---|---|---|---|
| persona bubble | `bg-primary p-md text-on-primary rounded-2xl rounded-tr-sm shadow-soft` (`TurnBubble.tsx:71`) | `bg-surface-low border border-outline rounded-md rounded-tr-sm text-text-main` | right-aligned kept |
| persona header | `text-label-md … text-on-surface-variant "{name} · Persona"` + `Sym face` avatar `bg-primary/10` (`:43-48`) | `.hud text-text-dim "{name} · Persona"` + lucide `scan-face text-primary` in `bg-primary/10` | |
| app (RecBot) bubble | `border-border-soft bg-surface-container-lowest rounded-2xl rounded-tl-sm shadow-soft` (`:107`) | `bg-surface border border-outline rounded-md rounded-tl-sm` | left-aligned |
| app header | `Sym smart_toy` avatar `bg-surface-container-highest` + `"RecBot"` (`:51-57`) | lucide `brain-circuit text-primary` in `bg-surface-high` + **app-aware name** (see copy) `.hud text-primary` | |
| hiccup line | `text-error italic "RecBot did not return…"` (`:109-111`) | `text-danger italic` + rewritten copy | |
| markdown body | `text-body-md text-on-surface` (`:113`) | `text-[13px] leading-relaxed text-text-main` | |
| latency meta | `font-mono-sm text-on-surface-variant` + `Sym timer` (`:132-135`) | `font-mono text-[11px] text-text-dim` + lucide `timer`; optionally wrap as `.hud … border border-outline rounded px-2 py-1` (mockup `:319`) | real latency only — keep honest (no tokens/cost) |
| TurnMarker | `border-border-soft` + `text-label-md … tracking-widest text-on-surface-variant`, `bg-background` (`:145-152`) | `border-outline-dim` + `.hud text-text-dim`, center label on `bg-surface-dim` | |

### RecommendedItems

| element | current | target | notes |
|---|---|---|---|
| card | `border-border-soft rounded-lg` (`:36`) | `border border-outline rounded-md` | |
| header | `border-border-soft bg-surface-container-low` + `Sym {domainIcon} text-primary` + `.hud`-ish label (`:37-44`) | `bg-surface-low border-outline` + lucide domain icon `text-primary` + `.hud text-text-dim` | domain noun unchanged |
| count | `font-mono-sm text-on-surface-variant` (`:42`) | `font-mono text-[11px] text-text-dim` | |
| rank badge | `bg-primary/10 text-primary text-[11px] font-bold` (`:50`) | `bg-primary/10 text-primary font-mono font-bold` | |
| title | `text-body-md text-on-surface` (`:57`) | `text-[12px] font-semibold text-text-main` | |
| id chip | `bg-surface-container font-mono-sm text-on-surface-variant` (`:60`) | `bg-surface-high font-mono text-[11px] text-text-dim` | |
| row hover | `hover:bg-surface-container-low` (`:48`) | `hover:bg-surface-low hover:border-primary/60` | |
| (optional) "Best match" tag on rank 1 | — | `.hud text-secondary border border-secondary/25 bg-secondary/10` corner tag | presentational; mockup `:316` |
| domain icons (`DOMAIN_META :16-20`) | `movie`/`stadia_controller`/`self_care` | `clapperboard`/`gamepad-2`/`sparkles` | |

### ToolPlanFold

| element | current | target | notes |
|---|---|---|---|
| container | `border-outline-variant bg-surface-container-low(low/lowest)` (`:58-60`) | `border-outline bg-surface-low` (open: `bg-surface-lowest`) | |
| header button | `text-label-md … text-on-surface-variant` + `Sym code` + chevron; hover `bg-surface-variant` (`:67-75`) | `.hud text-text-dim` + lucide `braces` + `chevron-down/up`; hover `bg-surface-high` | label rewrite below |
| "Tool plan" / "Ranked items · scores" headers | `text-[11px] uppercase tracking-wider text-on-surface-variant` (`:88,104`) | `.hud text-text-dim` | |
| step rows | `text-body-sm text-on-surface` + `Sym {tool} text-primary` + `font-mono-sm` (`:91-95`) | `font-mono text-[11px] text-text-variant` + lucide tool icon `text-primary` | tool-icon map → lucide (see Icon map) |
| ranked scores | `font-mono-sm text-on-surface-variant`, value `text-on-surface` (`:107-114`) | `font-mono text-[11px] text-text-dim`, value `text-text-variant` | |
| raw `<pre>` | `bg-surface font-mono-sm text-on-surface-variant` (`:122`) | `bg-field font-mono text-[11px] text-text-variant` | matrAIx code surface = `field` |
| empty body | "No tool plan or raw action…" `text-on-surface-variant` (`:81`) | `text-text-dim` + rewritten copy | |

---

## H. Inspector — Scorecard (Evaluation tab) — `Scorecard.tsx`

Overall 0–10 + Constraint 0–5 + Preference 0–5 + clarifying-Qs + metric tiles. Tab
chrome (`InspectorTabs`) is owned by the inspector/shared section; here we restyle the
Evaluation panel body. Scoring honesty rules (`:9-16`) are preserved.

| element | current | target | notes |
|---|---|---|---|
| card | `border-border-soft bg-surface-container-lowest shadow-soft rounded-xl` (`:61`) | `.panel bg-surface-lowest border border-outline rounded-md` | |
| card header | `border-border-soft bg-surface-container-low` + `Sym verified text-primary` + `text-headline-sm … uppercase` (`:63-67`) | `bg-surface-low border-outline` + lucide `shield-check text-primary` + `.hud text-primary "Evaluation"` | |
| "Completed" pill | `bg-success` dot + `text-on-surface-variant` (`:68-71`) | `bg-secondary` dot + `.hud text-text-dim` | |
| overall block | `border-l border-border-soft pl-3` (`:92`) | add `border-l-2 border-l-{band}` accent (mockup `:355` uses `border-l-4 border-l-secondary`) | band-colored |
| overall number | `text-[40px] font-bold tabular-nums {band.text}` (`:79`) | `font-display text-[44px] font-bold tabular-nums {band.text}` | Space Grotesk; band via SCORE_BAND_CLASS |
| "/ 10" | `text-headline-md font-headline-md text-on-surface-variant` (`:82`) | `text-[13px] text-text-dim` | |
| "Persona self-rating" | `text-[10px] uppercase tracking-wider text-on-surface-variant` (`:84`) | `.hud text-text-dim` | |
| rating quote | `text-body-md italic text-on-surface` (`:93`) | `text-[12px] italic leading-relaxed text-text-variant` | |
| criterion label | `text-body-sm font-medium text-on-surface` + state icon (`:158-165`) | `text-[12px] font-medium text-text-main` + lucide `check-circle`/`minus-circle`/`x-circle` in `{band.text}` | |
| criterion score | `text-body-sm font-semibold {band.text}` (`:167`) | `font-mono text-[12px] font-bold {band.text}` | |
| criterion bar track | `bg-surface-container-high` (`:171`) | `bg-field` | |
| criterion bar fill | `{band.bar}` (`:172`) | `{band.bar}` (mint/warn/danger) | |
| rationale | `text-body-sm text-on-surface-variant` (`:174`) | `text-[11px] text-text-dim leading-snug` | |
| clarifying (asked) | `border-success/40 bg-success-container` + `Sym help text-on-success-container` (`:184,191`) | `border-secondary/40 bg-secondary/10` + lucide `circle-help text-secondary` | |
| clarifying (none) | `border-border-soft bg-surface-container-low` (`:184`) | `border-outline-dim bg-surface-low text-text-dim` | |
| metric tile | `border-border-soft bg-surface-container-low` + `text-headline-md font-headline-md` value (`:205-209`) | `border border-outline bg-surface rounded-md` + `font-display text-[22px] font-bold` value + `.hud text-text-dim` caption | mockup `:357-359` |
| skeleton `:215-237` | `animate-rb-pulse bg-surface-container/-high` | same shimmer on `bg-surface-high`/`bg-surface-low` | warming/running |
| **empty / no-eval** `:41-53` | dashed `border-border-soft bg-surface-container-low` + `Sym fact_check text-outline` | dashed `border-outline-dim bg-surface-low` + lucide `clipboard-check text-text-dim` | copy rewrite (two variants) |

(`GroundingChip` from `runsShared` is reused at `:89` — it inherits the shared chip
reskin owned by the runs/shared section; flagged here for visibility.)

> Companion inspector panels in the same tab strip — **Persona** (`PersonaPanel.tsx`)
> and **Prompts** (`PromptPanel.tsx`) — get the same token swap: avatar tile
> `bg-primary/10` + lucide `scan-face`; section headers `.hud text-text-dim`
> underlined `border-outline-dim`; context/`<pre>` blocks on `bg-surface-low`
> (Persona) / `bg-field` (Prompts). Their empty states are in the copy table.

---

## States summary (empty · warming · running · done · error)

| surface | empty (no persona) | warming (`building`) | running | done | error/timeout |
|---|---|---|---|---|---|
| Pipeline | Persona "Choose a persona" (idle); others "Ready"/"Waiting" | Chatbot "Warming up" (active/primary); Persona "Getting ready" | active node primary per phase | all mint "Done" | danger tone + node status |
| Trajectory | teaching empty (users icon) | skeleton turn + warming label | streaming bubbles + thinking line | "Run complete" mint marker | danger banner + Retry |
| Scorecard | "Run an eval…" empty | shimmer skeleton | shimmer skeleton | full card | "ended before an evaluation…" |
| Run CTA | disabled | "Running…" + spinner | "Running…" + spinner | "Re-run eval" | "Re-run eval" |

---

## Copy rewrites

Tone: friendly, lightly tutorial, never cute. Mono `.hud` labels stay real words.

### Labels & controls

| location | current text | friendly rewrite |
|---|---|---|
| TaskTypeSwitch `:20` | "Application type" | "What are you testing?" |
| TaskTypeSwitch options `:12-14` | Chatbot / Survey / Web | Chatbot / Survey / Website (keep short; tooltips below) |
| Application picker header | "Application" / "3 adapters" | "Pick an app to test" / "3 available" |
| RunConfigBar `:171` (panel title) | "Run configuration" | "Run options" |
| Knob `engine` `RunConfigBar.tsx:113` | "Application model" | "App's model" (helper: "The AI model the app under test runs on.") |
| Knob `personaModel` `:120` | "Persona model" | "Simulated-user model" (helper: "The model that role-plays your chosen persona.") |
| Knob `domain` `:130` | "Domain" | "Catalog" + suffix "· RecAI only" (helper: "Which item library RecAI recommends from.") |
| Knob `goalContext` `:139` | "Conversation style" | "How the user behaves" (helper: "The mood and goal the simulated user brings to the chat.") |
| Slider `:154` | "Max turns:" | "Conversation length (max turns):" (helper: "How many back-and-forth exchanges before we stop.") |
| RunHeader title fallback `RunHeader.tsx:45` | "No persona selected" | "No persona chosen yet" |
| Run CTA `RunHeader.tsx:88` | "Run eval" / "Re-run eval" / "Running…" | "Run simulation" / "Run again" / "Running…" |
| Export `:75` | "Export log" | "Download transcript" |
| Runs `:66` | "Runs" | "Past runs" |
| App-reply speaker `TurnBubble.tsx:56` | "RecBot" (hardcoded) | app-aware: "RecAI" / "OpenBB" / "Medical Assistant" (fallback "The app") — pass app display name down (presentational) |
| ToolPlanFold header `:73` | "Tool plan / raw action" | "How the app decided (tools & raw output)" |
| ToolPlanFold sect `:88` | "Tool plan" | "Steps the app took" |
| ToolPlanFold sect `:104` | "Ranked items · scores" | "Candidates it ranked, with scores" |
| Scorecard header `:66` | "Evaluation" | "Scorecard" |
| Scorecard pill `:71` | "Completed" | "Scored" |
| Scorecard `:85` | "Persona self-rating" | "How the user rated it" |
| Criterion `:103` | "Constraint satisfaction" | "Did it respect the must-haves?" |
| Criterion `:109` | "Preference satisfaction" | "Did it match their tastes?" |
| Clarifying `:194-196` | "Clarifying questions — asked useful ones / none asked" | "Follow-up questions — asked helpful ones / didn't ask any" |
| Metric `:126` | "Turns to first rec" | "Turns to first suggestion" |
| Metric `:128` | "Turns" | "Total turns" |
| Metric `:129` | "Items recommended" | "Items suggested" |
| EnvPopover header `:93` | "Harbor environment" | "Test environment (Harbor)" + Read-only chip |
| EnvPopover `:107` | "Application stack" | "What's running inside the app" |
| EnvPopover `:122` | "Prompt boundary" | "Who writes which prompt" |
| EnvPopover rows `:48-67` | Runtime / Selection / Agent / Resources / Scorer / Cache / System prompt / Task prompt | keep as `.hud` (real words) — see tooltips below |
| Pipeline Scorer detail `ComponentPipeline.tsx:121` | "persona_self_report.json -> user_feedback.json" | "Turns the user's self-report into the final scores." |
| Pipeline owner strings `:104,111,119` | "PersonaEval task controller" / "chatbot-api sidecar" / "PersonaEval self-report scorer" | keep mono (they're real component names) but the *detail* line stays friendly |

### Status microcopy (`ComponentPipeline.tsx`, `liveStatusLine`)

| location | current | friendly rewrite |
|---|---|---|
| Persona `:30` | "Select persona" | "Choose a persona" |
| Persona/Chatbot `:34,49` | "Preparing" / "Warming" | "Getting ready" / "Warming up" |
| Chatbot `:56` | "Serving chat" | "Replying" |
| Chatbot `:57` | "Conversation open" / "Waiting" | "Chatting" / "Waiting its turn" |
| Scorer `:68,71` | "Awaiting score" / "Scoring" / "Waiting" | "Not scored yet" / "Scoring" / "Waiting its turn" |
| any `:32,47` | "Interrupted" / "Check run" / "Pending artifacts" | "Stopped early" / "Needs a look" / "Nothing to score" |
| liveStatus `PersonaEvalCockpit.tsx:58` | "Warming the chatbot application — this first turn can take a minute." | "Starting the app — the first reply can take up to a minute." |
| liveStatus `:61` | "Persona is thinking…" | "The simulated user is typing…" |
| liveStatus `:63` | "Chatbot application is thinking…" | "The app is thinking…" |
| liveStatus `:64` | "Scoring the conversation…" | "Scoring how it went…" |

### Empty / error / teaching states

| location | current | friendly rewrite |
|---|---|---|
| Trajectory empty `:93-97` | "Pick a persona to begin" / "Choose one of the curated personas… run the eval to watch a persona drive a real conversation against RecBot." | "Start by choosing who to simulate" / "Pick a persona on the left and an app to test, set your run options, then hit **Run simulation** — you'll watch a stand-in user chat with the app, turn by turn." |
| Trajectory ready `:198-202` | "Ready to run" / "Press R or use the Run button…" | "All set" / "Press **R** (or the Run button) to start the simulation for this persona." |
| Trajectory failed `:163-165` | "This run didn't finish" / "The PersonaEval run stopped unexpectedly. Your configuration is unchanged." | "The simulation didn't finish" / "It stopped before completing — your settings are untouched, so you can try again right away." |
| Trajectory skeleton `:146` | "Warming the chatbot application…" | "Starting the app…" |
| Scorecard empty `:48-51` | "Run an eval to see the persona's scorecard here." / "This run ended before an evaluation was produced." | "Run a simulation and the scores will appear here." / "This run stopped before it could be scored." |
| ToolPlanFold empty `:82` | "No tool plan or raw action was recorded for this turn." | "The app didn't expose any internal steps for this turn." |
| TurnBubble hiccup `:110` | "RecBot did not return a reply for this turn." | "The app didn't reply on this turn." |
| TurnBubble `:73` | "(no message)" | "(the user said nothing)" |
| PersonaPanel empty `PersonaPanel.tsx:67-69` | "Select a persona from the catalog to see its profile." | "Choose a persona to see who you're simulating." |
| PromptPanel empty `PromptPanel.tsx:15-17` | "Run an eval to see the Harbor and task prompts." | "Run a simulation to see the exact prompts used." |

### New helper text, tooltips & first-run hints

- **Launch hint** (new, under the Run CTA — required): *"A simulated user chats with
  the app for a few turns, then rates how well it understood and met their needs."*
  Make it app-aware where natural; the Survey/Web variants (for the shared CTA) are
  *"…answers the whole questionnaire, then we check the responses are complete and
  consistent."* and *"…browses the site to finish the task — you get UX ratings plus a
  replayable step-by-step trace."*
- **Pipeline intro** (new, first-run only, above the nodes): *"Your run flows left to
  right: the **Persona** plays the user, the **Chatbot** is the app you're testing, and
  the **Scorer** rates the result."*
- **Knob tooltips** (on the `.hud` labels): App's model → *"The model powering the app
  under test."* · Simulated-user model → *"The model that role-plays your persona."* ·
  Catalog → *"Only RecAI recommends from a catalog, so this appears for RecAI."* · How
  the user behaves → *"Sets the simulated user's goal and mood — e.g. exploratory vs.
  goal-directed."* · Conversation length → *"We stop after this many exchanges even if
  the chat isn't resolved."*
- **App-type tooltips**: Chatbot → *"A back-and-forth conversation."* · Survey → *"A
  fixed questionnaire the user fills out."* · Website → *"A real browser task the user
  completes."*
- **Environment "Read-only" chip tooltip**: *"These are fixed by the Harbor test
  sandbox and can't be changed for this run."*
- **Env row tooltips**: Selection → *"How the app picks candidate items."* · Agent →
  *"The agent that drives the app."* · Resources → *"The data the agent draws on."* ·
  Scorer → *"Turns the user's self-report into scores."*
- **Scorecard scale hint** (small, once): *"Scores read green when the app did well,
  amber when so-so, red when it missed."*
- **Export tooltip**: *"Save this conversation and its scores as a JSON file."*


---

# 04 — PersonaEval cockpit: Survey + Web

Reskin spec for the two non-chatbot cockpits:

- `src/components/cockpit/SurveyEvalCockpit.tsx` (603 lines)
- `src/components/cockpit/WebEvalCockpit.tsx` (683 lines)

This is a **pure in-place reskin**: the hooks (`useSurveyEval`, `useWebEval`), the TanStack queries (`listSurveyInstruments`, `listWebEvalTasks`), the export logic, every prop, and the sub-component tree all stay exactly as written. We only (a) swap the Material-3-style token classes for matrAIx tokens, (b) add the missing loading/error/live/empty states, and (c) rewrite all user-facing copy to teach a first-time user. No data-layer or behavior change.

## 0. What is preserved (per-option truths)

These are affirmed, not changed:

- **No environment panel** on either cockpit. Neither file imports `EnvironmentPopover`; do not add one. The Harbor environment facts are Chatbot-only.
- **Survey pipeline = Persona → Survey → Artifact** (3 nodes, `SurveyPipeline` `SurveyEvalCockpit.tsx:274-302`).
- **Web pipeline = Persona → Website → Trace → Evaluation** (4 nodes, `WebPipeline` `WebEvalCockpit.tsx:296-333`).
- **Survey scoring = completion `n/n` + valid flag + mean Likert** (`SurveyCompletion`, rendered `SurveyEvalCockpit.tsx:507-511`).
- **Web scoring = need-fit /10 + ease-of-use /10 + overall-UX /10 + selected product + browser trace (steps, screenshots, actions)** (`WebResult` + `WebTrace`, rendered `WebEvalCockpit.tsx:487-491, 499-515`).

The friendly relabelling below renames the *display text* of the `Trace` and `Artifact` nodes for first-time readers; the canonical node identity and ordering are unchanged and are noted in the mapping rows.

## 1. Shared primitives reused from section 03

Survey + Web are structurally clones of the Chatbot cockpit, so most chrome is **already shared** and is reskinned once in section 03 — do not re-spec it here, just consume the reskinned version:

| Primitive | File | Reskinned in |
| --- | --- | --- |
| Run-header shell (title + codename chip + Export/Run buttons) | inline `SurveyEvalCockpit.tsx:142-171`, `WebEvalCockpit.tsx:156-189` | §03 run-header recipe |
| `TaskTypeSwitch` (Application type segmented control) | `TaskTypeSwitch.tsx` | §03 |
| `KnobSelect` (config dropdown) | `KnobSelect.tsx` | §03 |
| `InspectorTabs` (right rail: Evaluation / Persona / Prompts) | `InspectorTabs.tsx` | §03 |
| `PersonaCatalog`, `PersonaDrawer`, `PersonaPanel`, `PromptPanel` | respective files | §03 |
| `Sym` glyph + `FOCUS_RING` | `cockpitShared.tsx:30, 55` | §03 / design-system |
| Pipeline node card + `toneClass` | duplicated `SurveyEvalCockpit.tsx:308-341`, `WebEvalCockpit.tsx:339-372`, `ComponentPipeline.tsx:76-81,132-153` | §03 (canonical recipe below) |
| `MetricTile` | duplicated `SurveyEvalCockpit.tsx:584-593`, `WebEvalCockpit.tsx:662-671` | §03 (canonical recipe below) |

**Consolidation note (recommended, optional):** `toneClass`, `PipelineTone`, and `MetricTile` are copy-pasted across `SurveyEvalCockpit`, `WebEvalCockpit`, and `ComponentPipeline`. The reskin is a good moment for §03 to promote them into `cockpitShared.tsx` (or a `PipelineStrip`/`MetricTile` export) so all three import one definition. If they stay duplicated, **every copy must adopt the identical matrAIx classes below** so the three pipelines never drift.

## 2. Token migration quick-reference (subset used by these two files)

Authoritative map lives in the design-system section; this is only the subset these files touch. Apply it everywhere in both files unless a row below overrides it.

| Current class | matrAIx target |
| --- | --- |
| `bg-background` | `bg-surface-dim` |
| `bg-surface-container-lowest` (header / rails / banners) | `bg-surface-lowest` |
| `bg-surface-container-lowest` (a *card* surface) | `bg-surface` |
| `bg-surface-container-low` | `bg-surface-low` |
| `bg-surface-container` | `bg-surface-high` |
| `bg-surface-container-high` | `bg-surface-high` |
| input / code surface | `bg-field` |
| `border-border-soft` | `border-outline-dim` (hairlines) / `border-outline` (card edges) |
| `border-outline-variant` | `border-outline` |
| `text-on-surface` | `text-text-main` |
| `text-on-surface-variant` | `text-text-variant` |
| `text-outline` (dim icon) | `text-text-dim` |
| `bg-primary` / `text-on-primary` | unchanged (same token names) |
| `hover:bg-primary-container` | `hover:bg-primary-dim` |
| success: `text-success` / `bg-success` / `bg-success-container` / `text-on-success-container` | `text-secondary` / `bg-secondary` / `bg-secondary/10` / `text-secondary` |
| error: `text-error` / `bg-error-container` / `text-on-error-container` | `text-danger` / `bg-danger/10` / `text-danger` |
| warning: `text-warning` / `bg-warning-container` | `text-warn` / `bg-warn/10` |
| `text-display font-display` | `font-display text-[26px] font-bold tracking-tight` |
| `text-headline-sm font-headline-sm` | `font-display text-[15px] font-semibold` |
| `text-headline-md font-headline-md` (metric value) | `font-display text-[24px] font-bold` |
| `text-label-md font-label-md uppercase tracking-wider` (micro-label) | `hud text-[9px] text-text-dim` |
| `text-[10px] uppercase tracking-wider` (tile caption) | `hud text-[9px] text-text-dim` |
| `font-mono-sm text-mono-sm` | `font-mono text-[11px]` |
| `shadow-soft` / `shadow-sm` / `shadow-pop` | drop (matrAIx is flat: borders + `.panel` bracket); keep `shadow-2xl` only on floating menus |
| `animate-rb-pulse` + `bg-surface-container` skeleton | `animate-pulse bg-surface-high` |
| `animate-rb-spin` | `animate-spin` (spinner glyph) |
| `rounded-xl` (cards) | `rounded-md` |

**Canonical matrAIx recipes** referenced by the tables below (define once, in §03 if consolidated):

- **Panel card** → `panel bg-surface border border-outline rounded-md` (the `.panel` class draws the top-left cyan corner bracket).
- **Panel header strip** → inner `border-b border-outline px-4 py-3`, title `hud text-[10px] text-text-dim` (or `text-primary` for the panel's lead heading), trailing count `hud text-[9px] text-text-dim`.
- **Inset sub-tile** → `rounded border border-outline bg-surface-low px-3 py-2.5`.
- **Pipeline `toneClass`** → active `border-primary/40 bg-primary/10 text-primary` · done `border-secondary/30 bg-secondary/10 text-secondary` · error `border-danger/30 bg-danger/10 text-danger` · idle `border-outline-dim bg-surface-high text-text-dim`.
- **Status pill** → `shrink-0 rounded border px-1.5 py-0.5 hud text-[9px]` + tone class.
- **`MetricTile`** → `rounded-md border border-outline bg-surface p-4`; value `font-display text-[24px] font-bold tabular-nums text-text-main`, unit suffix `font-sans text-[12px] text-text-dim`, caption `hud text-[9px] text-text-dim`. **Lead/primary tile** adds `border-l-4 border-l-secondary` and caption `text-secondary`.
- **Validity badge** → valid `text-secondary border-secondary/30 bg-secondary/10`; invalid `text-danger border-danger/30 bg-danger/10`; both `hud text-[8px] rounded px-1.5 py-0.5 border`.
- **Primary CTA** → `bg-primary text-on-primary hover:bg-primary-dim glow` + `FOCUS_RING` (the single glowing CTA per screen).
- **Empty/teaching card** → `rounded-md border border-dashed border-outline bg-surface-low`; icon in `bg-primary/10 text-primary` rounded square.
- **Error card** → `border border-danger/30 bg-danger/10`; icon + heading `text-danger`; retry button `border border-danger/40 bg-danger/10 text-danger hover:bg-danger/20`.

---

## A. Survey cockpit (`SurveyEvalCockpit.tsx`)

### A.1 Run header + config bar
Reuse the §03 run-header recipe verbatim (`:142-171`). Only the button copy is Survey-specific: see Copy table (`Run survey` / `Re-run survey` / `Export log`). `SurveyConfigBar` (`:214-254`) reuses reskinned `KnobSelect`; only the `label` strings change (Copy table) and each knob gains a teaching tooltip (§Copy table 2).

### A.2 `SurveyPipeline` — 3 nodes (`:256-332`)

| Element | Current | Target matrAIx | Notes |
| --- | --- | --- | --- |
| Section wrapper `:305` | `border-b border-border-soft bg-surface-container-lowest px-lg py-2.5` | `border-b border-outline-dim bg-surface-lowest px-lg py-2.5` | — |
| Node card `:309` | `rounded-md border border-border-soft bg-surface-container-low px-3 py-2` | `rounded-md border border-outline bg-surface-low px-3 py-2` | — |
| Icon chip `:310` + status pill `:316` | `toneClass` (M3 container tokens) | canonical `toneClass` above | status pill text → `hud text-[9px]` |
| Node label `:315` | `text-label-md ... uppercase tracking-wider text-on-surface` | `hud text-[10px] text-text-main` | — |
| Owner line `:320` | `font-mono-sm text-mono-sm text-on-surface` | `font-mono text-[11px] text-text-variant` | now a friendly description (Copy table); keep raw artifact name in `title=` tooltip |
| Detail line `:321` | `text-body-sm text-on-surface-variant` | `text-[12px] text-text-variant leading-snug` | — |
| Arrow `:325` | `text-outline` | `text-text-dim` | swap glyph intent to `arrow-right`/`chevron-right` |

Node copy (display text only — identity unchanged): **Persona** / **Survey** / **Answers** (was "Artifact"). See Copy table for owner/detail/status rewrites.

### A.3 `InstrumentPreview` + question-type chips (`:416-443`)

| Element | Current | Target matrAIx | Notes |
| --- | --- | --- | --- |
| Section `:418` | `rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft` | `panel bg-surface border border-outline rounded-md` | gains corner bracket |
| Header `:419-422` | `border-b border-border-soft bg-surface-container-low px-4 py-3` | `border-b border-outline px-4 py-3`; add a `hud text-[10px] text-text-dim` eyebrow ("Questionnaire preview") above the data title; trailing `hud text-[9px] text-text-dim` shows `{n} questions` | — |
| Title `:420` | `text-headline-sm font-headline-sm text-on-surface` | `font-display text-[15px] font-semibold text-text-main` | data |
| Description `:421` | `text-body-sm text-on-surface-variant` | `text-[12px] text-text-variant leading-snug` | data |
| Question row `:425` | `grid ... px-4 py-3` divided by `divide-border-soft` | same grid; `divide-outline-dim`; on hover `hover:bg-surface-low` | — |
| `Q{n}` `:426` | `font-mono-sm ... text-on-surface-variant` | `hud text-[10px] text-text-dim` | matches mockup `Q1` |
| Prompt `:428` | `text-body-md text-on-surface` | `text-[13px] text-text-main leading-relaxed` | — |
| Options line `:430` | `text-body-sm text-on-surface-variant` | `text-[11px] text-text-variant` | "Options:" → "Choices:" (Copy) |
| **Type badge `:435-437`** | neutral `border-border-soft bg-surface-container ... {question.type}` | **type-colored `hud text-[8px] rounded px-1.5 py-0.5 border`**: `likert`→`text-primary border-primary/30 bg-primary/10`; `single_choice`→`text-secondary border-secondary/30 bg-secondary/10`; `multi_choice`→`text-warn border-warn/30 bg-warn/10`; `free_text`→`text-text-dim border-outline bg-surface-high` | label maps raw enum → friendly chip word (Likert / Single / Multi / Free) with a teaching `title=` tooltip; mirrors mockup lines 201-204 |

Add a tiny `questionTypeMeta(type)` presentational map (label + tone + tooltip) — pure presentation, reads existing `question.type`, no data change.

### A.4 `SurveyArtifact` + `AnswerRow` (`:445-466`, `:537-566`)

| Element | Current | Target | Notes |
| --- | --- | --- | --- |
| Section `:447` | `rounded-xl ... bg-surface-container-lowest shadow-soft` | `panel bg-surface border border-outline rounded-md` | — |
| Header `:448` | `bg-surface-container-low px-4 py-3` | `border-b border-outline px-4 py-3` | title → "Completed questionnaire" (Copy) |
| Completion subline `:451` | `text-body-sm text-on-surface-variant` | `text-[12px] text-text-variant` | `{a} / {b} questions answered` kept |
| Valid badge `:455` | success/error container tokens | canonical Validity badge | + tooltip |
| `AnswerRow` value `:557` | `font-mono text-sm text-on-surface` | `font-mono text-[12px] text-text-main` | likert/choice value |
| `AnswerRow` questionId `:550` | `font-mono-sm text-mono-sm text-primary` | `font-mono text-[10px] text-primary` | — |
| `AnswerRow` rationale `:553` | `text-body-sm text-on-surface-variant` | `font-mono text-[11px] text-text-dim leading-relaxed` | matches mockup "persona rationale:" treatment |
| `AnswerRow` confidence `:559` | `font-mono-sm ... "confidence {n}%"` | `font-mono text-[11px] text-text-variant` → "{n}% sure" (Copy) | — |

### A.5 `SurveyResults` inspector panel (`:468-535`)

Lives in the right rail (`InspectorTabs` evaluation slot). Narrower padding than the workspace.

| Element | Current | Target | Notes |
| --- | --- | --- | --- |
| Skeleton `:480-484` | `animate-rb-pulse bg-surface-container rounded-xl` | `animate-pulse bg-surface-high rounded-md` | — |
| Empty card `:490` | `rounded-xl border-dashed border-border-soft bg-surface-container-low` | empty/teaching card recipe | copy rewrite |
| Summary section `:502` | `rounded-xl ... bg-surface-container-lowest shadow-soft` | `panel bg-surface border border-outline rounded-md` | header "Result summary" |
| Summary heading `:504` | `text-headline-sm ... uppercase tracking-wider` | `hud text-[10px] text-primary` | — |
| `verified` glyph `:505` | `text-success` / `text-error` | `text-secondary` / `text-danger` | — |
| 3 `MetricTile` `:508-510` | M3 tile | canonical `MetricTile` | captions: Answered / Valid / **Average rating** (was "Mean Likert", Copy + tooltip) |
| Answers + Trajectory sections `:513-532` | `rounded-xl ... shadow-soft`, `divide-border-soft` | `panel bg-surface border border-outline rounded-md`, `divide-outline-dim` | "Trajectory" heading → "Step-by-step log" (Copy) |
| `TrajectoryEventRow` `:568-582` | `{actor} / {action}`, `pre` on `bg-surface-container-low` | `{actor} · {action}` (Copy); `pre` → `bg-field font-mono text-[11px] text-text-variant rounded` | actor friendly-mapped (Copy) |

### A.6 Survey — NEW / missing states (ADD)

1. **Instruments loading** (`instrumentsQuery.isLoading`, currently unhandled — knob + preview just render empty). In the workspace, before `InstrumentPreview`, show 3 skeleton question rows (`animate-pulse bg-surface-high rounded-md h-12`) under a `hud` "Loading questionnaires…" caption.
2. **Instruments error** (`instrumentsQuery.isError`). Show the error-card recipe: "We couldn't load the questionnaires. Check your connection and try again." + Retry (`instrumentsQuery.refetch`).
3. **Live "answering" progress** (during `running`, replacing/augmenting the bare spinner at `:383-388`). Faithful to mockup `surveylive` (lines 731-759): a `hud text-[10px] text-primary` eyebrow, an animated spinner glyph, the line **"Simulated user is answering…"**, and a completion progress bar (`h-1.5 rounded-full bg-field` track + `bg-primary` fill). Width is driven only by existing data — `result?.completion.numAnswered / numQuestions` once partial results stream, else indeterminate shimmer; no new fetch.
4. **No-instrument preview placeholder** (when `instrument` is null but list resolved): teaching card "Pick a questionnaire above to preview its questions."
5. Reskin existing empty/failed states (`:363-377`, `:389-409`) to the canonical empty/error recipes with rewritten copy.

---

## B. Web cockpit (`WebEvalCockpit.tsx`)

### B.1 Run header + config bar
Same as A.1; button copy = `Run website test` / `Re-run website test`. `WebConfigBar` (`:234-274`) reuses `KnobSelect`; label "Website task" + teaching tooltip.

### B.2 `WebPipeline` — 4 nodes (`:276-363`)

Identical card/tone treatment as A.2 (same `toneClass`, same node-card classes at `:339-354`); grid is `2xl:grid-cols-4`. Display labels: **Persona** / **Website** / **Browser steps** (was "Trace") / **Evaluation**. Owner/detail/status rewrites in Copy table. Keep the canonical `Trace` node identity; relabel only the visible text and note it.

### B.3 `WebsiteTaskCard` + `InfoTile` (`:450-471`, `:673-680`)

| Element | Current | Target | Notes |
| --- | --- | --- | --- |
| Section `:452` | `rounded-xl ... bg-surface-container-lowest shadow-soft` | `panel bg-surface border border-outline rounded-md` | mirrors mockup lines 221-229 |
| Header `:453` | `bg-surface-container-low px-4 py-3` | `border-b border-outline px-4 py-3`; add `hud text-[10px] text-text-dim` eyebrow "Website task" + a one-line helper (Copy) | — |
| Site name `:456` | `text-headline-sm font-headline-sm` | `font-display text-[15px] font-semibold text-text-main` | data |
| Description `:457` | `text-body-sm text-on-surface-variant` | `text-[12px] text-text-variant leading-snug` | data |
| `task.id` badge `:459` | neutral mono chip | `hud text-[8px] text-text-dim border border-outline rounded px-1.5 py-0.5` | add `title="Task ID"` |
| `InfoTile` `:673-680` | `rounded-lg border-border-soft bg-surface-container-low`; label `text-[10px] uppercase`; value `font-mono-sm text-on-surface` | `rounded border border-outline bg-surface-low px-3 py-2.5`; label `hud text-[8px] text-text-dim`; value `font-mono text-[11px] text-text-main truncate` | labels: "Website URL" / "Results file" / "Browser recording" (Copy) |

### B.4 `WebArtifact` — score tiles + selected product + reason (`:473-497`)

| Element | Current | Target | Notes |
| --- | --- | --- | --- |
| Section `:475` | `rounded-xl ... shadow-soft` | `panel bg-surface border border-outline rounded-md` | — |
| Header `:476-485` | `bg-surface-container-low px-4 py-3` | `border-b border-outline px-4 py-3`; eyebrow `hud text-[10px] text-text-dim` "Visit results" | title/subline copy rewrite |
| Valid badge `:483` | success/error tokens | canonical Validity badge + tooltip | — |
| 3 score tiles `:487-491` | `MetricTile` with value `"{n}/10"` | canonical `MetricTile`, **split unit**: value `{n}` + `font-sans text-[12px] text-text-dim` "/10"; **Need fit = lead tile** (`border-l-4 border-l-secondary`, caption `text-secondary`) per mockup line 411 | captions Need fit / Ease of use / Overall UX kept (mockup-approved) + tooltips (Copy table 2) |
| Reason `:492` | `border-t border-border-soft ... text-on-surface-variant` | `border-t border-outline px-4 py-3 text-[13px] text-text-variant leading-relaxed` | data |

Optional enhancement (presentational only, reads existing scores): band the tile value color via `scoreBand(value/10)` + `SCORE_BAND_CLASS` from `cockpitShared.tsx:315-334` (now danger/warn/secondary). Keep off by default to stay faithful to the neutral-value mockup; mention as a toggleable signal.

### B.5 `WebResults` inspector panel (`:517-585`)
Same reskin rules as A.5 (skeleton → `animate-pulse bg-surface-high`; empty/sections → panel recipe; `verified` glyph → secondary/danger). Inspector tiles captions: Need fit / Ease / Overall. "Selected item" heading kept; "Trace" heading → "Browser recording".

### B.6 `WebTracePanel` + `TraceEventRow` — screenshots + actions (`:499-515`, `:587-660`)

Keep the disclosure-row structure and the expand-to-reveal interaction (good UX, accessible via `aria-expanded`); restyle only.

| Element | Current | Target | Notes |
| --- | --- | --- | --- |
| Panel `:501` | `rounded-xl ... shadow-soft` | `panel bg-surface border border-outline rounded-md` | header eyebrow `hud text-[10px] text-primary` + footprints/route glyph, mockup line 420 |
| Panel subline `:504-506` | `text-body-sm` "{n} preserved browser-agent events." | `text-[12px] text-text-variant` → "{n} steps the visitor took, with screenshots." (Copy) | — |
| Row container `:594` / divider `:508` | `divide-border-soft` | `divide-outline-dim`; row `hover:bg-surface-high` | — |
| Disclosure button `:598` | `hover:bg-surface-container-low` | `hover:bg-surface-low rounded-md` + `FOCUS_RING` | chevron glyph `text-text-dim` |
| Step label `:609-611` | `text-body-sm font-medium text-on-surface` "Step {n} \| {source}" | `hud text-[9px] text-text-dim` "Step {n} · {source}" (Copy: 'agent'→'visitor'); add a friendly action verb after the source via `summarizeAction` | mockup "Step 9 · click" |
| Actions count `:612-614` | `font-mono-sm` "{n} actions" | `font-mono text-[11px] text-text-variant` "{n} action(s)" | — |
| Message preview `:617` | `text-body-sm text-on-surface-variant` | `text-[12px] text-text-variant truncate` | — |
| Screenshot-file chip `:620-623` | `border-border-soft bg-surface-container` | `border-outline bg-surface-high hud text-[10px] text-text-dim` + image glyph | filename kept (honest) |
| Expanded screenshot `:630-642` | `rounded-md border-border-soft bg-surface-container-low`; `img` `bg-surface-container-lowest object-contain` | `rounded-md border border-outline bg-surface-low`; `img` `bg-surface-lowest object-contain`; **add `onError` → placeholder tile** (aspect-video `bg-surface-low grid place-items-center text-text-dim` + image glyph + "Screenshot unavailable") | matches mockup placeholder tiles 422-425 |
| Actions `pre` `:651-654` | `bg-surface-container-lowest font-mono-sm text-on-surface-variant` | `bg-field font-mono text-[11px] text-text-variant rounded` | — |

Add `summarizeAction(event)` — presentational helper deriving a verb (`click` / `type` / `navigate` / …) and a `name(args)` one-liner from the existing `event.actions[0]`. No data change; powers the friendlier step labels and matches the mockup's `goto(/store)` / `add_to_cart()` captions.

Optional enhancement: a **screenshot gallery grid** (`grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3` of thumbnail cards, mockup lines 421-426) for the wide workspace `WebTracePanel`, while the narrow inspector keeps the compact disclosure list. Clearly optional — the disclosure-list reskin is the required deliverable.

### B.7 Web — NEW / missing states (ADD)

1. **Tasks loading** (`tasksQuery.isLoading`): skeleton `WebsiteTaskCard` (header bar + 3 info-tile skeletons, `animate-pulse bg-surface-high`) under a `hud` "Loading website tasks…" caption.
2. **Tasks error** (`tasksQuery.isError`): error-card recipe — "We couldn't load the website tasks. Check your connection and try again." + Retry (`tasksQuery.refetch`).
3. **Live "browsing" progress** (during `running`, augmenting the spinner `:416-421`): eyebrow + spinner + **"Simulated visitor is browsing…"**, and a live step counter "Recorded {n} steps so far" driven by `trace?.events.length` as events stream (no new fetch).
4. **Empty trace** (run `done` but `trace.events.length === 0`): inside `WebTracePanel`, a single muted row "This run finished without recording any browser steps."
5. **Screenshot fallback** (B.6 `onError`) for steps whose `screenshotUrl` 404s or is absent.
6. Reskin existing empty/failed states (`:396-410`, `:422-442`) to canonical recipes with rewritten copy.

---

## 3. Icon intent mapping

The shared `Sym` primitive (Material Symbols) is converted to the matrAIx lucide set in §03 / design-system; this section only declares the **intent** per unique glyph so it survives whichever primitive lands:

| Usage | Current `Sym name` | matrAIx lucide intent |
| --- | --- | --- |
| Survey node / empty / type switch | `fact_check`, `groups` | `clipboard-check`, `users` |
| Website node / empty | `language` | `globe` |
| Trace node | `route` | `footprints` |
| Evaluation node | `rate_review` | `gauge` |
| Answered / validity | `verified` | `circle-check` / `badge-check` |
| Selected product | (header text only) | `package` |
| Screenshot thumb + chip | `image` | `image` |
| Running spinner | `autorenew` + `animate-rb-spin` | `loader-2` + `animate-spin` |
| Retry | `refresh` | `rotate-cw` |
| Disclosure | `chevron_right` / `expand_more` | `chevron-right` / `chevron-down` |

## 4. Theming (light/dark)

No per-component work beyond using the token classes above — every class resolves through CSS-variable tokens, so the light/dark toggle (added globally in the design-system/app-shell section) flips both cockpits automatically. Two checks specific to these files: (a) the type-chip and validity tints use `/10` opacity backgrounds that read in both themes; (b) if the optional `scoreBand` value-coloring is enabled, it already uses the contrast-safe darker text variant in light mode (`cockpitShared.tsx:329-334`).

---

## 5. Copy rewrites

### 5.1 Existing user-facing text → friendly rewrite

| Location (file:line) | Current text | Friendly rewrite |
| --- | --- | --- |
| Survey status `:37-42` | "Preparing the survey respondent environment…" | "Setting up the questionnaire…" |
| Survey status `:41` | "Collecting survey artifact…" | "Saving the answers…" |
| Survey status `:42` | "Persona agent is completing the survey…" | "The simulated user is filling out the questionnaire…" |
| Survey status `:42` | "Running the survey task…" | "Running the questionnaire…" |
| Header title fallback `:84` | "No persona selected" | "No persona chosen yet" |
| Run button `:168` | "Run survey" / "Re-run survey" / "Running…" | "Run questionnaire" / "Run it again" / "Working…" |
| Export button `:159` | "Export log" | "Download results" |
| Config label `:235` | "Survey instrument" | "Questionnaire" |
| Config label `:246`, web `:264` | "Persona model" | "Simulated-user model" |
| Survey node owner `:278` | "Persona task runtime" | "The simulated user" |
| Survey persona detail `:279` | "{model} · persona prompt injection" | "Acts as the user, guided by the persona profile" (keep `{model}` as a mono caption) |
| Survey node owner `:287` | "survey_form task" | "Questionnaire form" (keep `survey_form` in `title=`) |
| Survey survey detail `:288` | "Load survey instrument" | "Choose a questionnaire to preview it" |
| Survey survey status `:290` | "Collecting responses" / "Check run" | "Filling it in" / "Needs a look" |
| Survey node label `:296` | "Artifact" | "Answers" |
| Survey artifact owner `:296` | "survey_result.json" | "Saved answers" (keep filename in `title=`) |
| Survey artifact detail `:296` | "answers + trajectory + completion" | "The answers, a step-by-step log, and a completeness check" |
| Survey artifact status `:299` | "Missing artifact" / "Available" / "Waiting" | "No answers yet" / "Ready to view" / "Waiting" |
| Pipeline statuses (both) | "Interrupted" | "Stopped" |
| Survey empty heading `:370` | "Pick a persona to begin" | "Choose a persona to start" |
| Survey empty body `:371-373` | "Choose a persona and a survey instrument, then run the survey to collect the persona's structured response." | "Pick a persona on the left and a questionnaire above, then press Run. A simulated user will fill it out and you'll see its answers and ratings." |
| Survey failed heading `:394` | "This survey run didn't finish" | "The questionnaire didn't finish" |
| Survey failed body `:396` | "The survey run stopped unexpectedly. Your configuration is unchanged." | "Something interrupted the run. Your setup is still here — press Try again." |
| Retry button (both) `:404,:437` | "Retry" | "Try again" |
| Instrument options line `:431` | "Options: {…}" | "Choices: {…}" |
| Type badge `:436` | raw `likert` / `single_choice` / `multi_choice` / `free_text` | "Likert" / "Single" / "Multi" / "Free" (+ tooltips, 5.2) |
| Survey artifact header `:450` | "Survey artifact" | "Completed questionnaire" |
| Valid/Incomplete badge `:456` | "Valid" / "Incomplete" | "Complete" / "Incomplete" (+ tooltip) |
| Answer confidence `:560` | "confidence {n}%" | "{n}% sure" |
| Inspector empty `:493` | "Run a survey to see the persona's completed answers here." | "Run a questionnaire to see the simulated user's answers and ratings here." |
| Inspector summary heading `:504` | "Survey result" | "Result summary" |
| Metric caption `:510` | "Mean Likert" | "Average rating" |
| Inspector heading `:525` | "Trajectory" | "Step-by-step log" |
| Trajectory row `:573` | "{actor} / {action}" | "{actor} · {action}" (map `agent`→"Simulated user", `system`→"System", `scorer`→"Scorer") |
| Web status `:43` | "Preparing the website test environment..." | "Setting up the website test…" |
| Web status `:46` | "Collecting website artifact and browser trace..." | "Saving the results and browser recording…" |
| Web status `:47` | "Persona agent is using the website..." | "The simulated visitor is using the site…" |
| Web status `:48` | "Running the website test..." | "Running the website test…" |
| Web run button `:186` | "Run website test" / "Re-run website test" | "Run website test" / "Run it again" |
| Web persona detail `:301` | "{model} \| browser/computer-use persona" | "Acts as a visitor, clicking and typing in a real browser" (keep `{model}` mono) |
| Web website status `:312` | "Being tested" | "In use" |
| Web trace node label `:316` | "Trace" | "Browser steps" |
| Web trace owner `:318` | "Harbor browser trajectory" | "Browser recording" (keep raw in `title=`) |
| Web trace detail `:319` | "actions + messages + raw browser trace" | "Every click, keystroke, and screenshot the visitor made" |
| Web trace status `:321` | "Recording" / "Check trace" | "Recording steps" / "Needs a look" |
| Web evaluation owner `:327` | "Persona self-report" | "The visitor's own rating" |
| Web evaluation detail `:328` | "need satisfaction + ease of use + UX rating" | "Whether the site met the need, how easy it was, and the overall experience" |
| Web evaluation status `:330` | "Missing artifact" | "No rating yet" |
| Web empty body `:404-406` | "Choose a persona and a website task, then run the browser test to collect the trace and experience rating." | "Pick a persona and a website task, then press Run. A simulated visitor will browse the site; you'll see every step it took and how it rated the experience." |
| Web failed heading `:427` | "This website test did not finish" | "The website test didn't finish" |
| Web failed body `:429` | "The website test stopped unexpectedly. Your configuration is unchanged." | "Something interrupted the test. Your setup is still here — press Try again." |
| InfoTile label `:466` | "Output artifact" | "Results file" |
| InfoTile `:467` | "Trace source" / "Harbor browser trajectory" | "Recording" / "Browser recording" |
| Web artifact heading `:478` | "Website evaluation artifact" | "Visit results" |
| Web artifact subline `:480` | "Selected {name} ({id})" | "The visitor chose {name}" (id → mono caption) |
| Valid/Invalid badge `:483` | "Valid" / "Invalid" | "Complete" / "Incomplete" (+ tooltip) |
| Web trace panel heading `:503` | "Website trace" | "Browser recording" |
| Web trace subline `:505` | "{n} preserved browser-agent events." | "{n} steps the visitor took, with screenshots." |
| Trace step label `:610` | "Step {n} \| {source or 'agent'}" | "Step {n} · {source or 'visitor'}" |
| Trace actions count `:613` | "{n} actions" | "{n} action(s)" |
| Web inspector empty `:542` | "Run a website test to see UX scores, selected item, and trace here." | "Run a website test to see scores, the chosen item, and the browser recording here." |
| Web inspector heading `:552` | "Website result" | "Result summary" |
| Web inspector heading `:563` | "Selected item" | "What the visitor chose" |
| Web inspector heading `:574` | "Trace" | "Browser recording" |

### 5.2 NEW helper / empty / tooltip / first-run copy (ADD)

| Where | New copy |
| --- | --- |
| First-run hint banner under Survey config bar (dismissible, shown until first run) | "New here? Pick a persona on the left and a questionnaire above, then press Run. PersonaEval plays a simulated user who fills out the form, and you'll see its answers and ratings." |
| First-run hint banner under Web config bar | "New here? Pick a persona and a website task, then press Run. PersonaEval plays a simulated visitor who browses the site, and you'll see each step and how it rated the experience." |
| Questionnaire knob tooltip | "The questionnaire the simulated user will fill out." |
| Website-task knob tooltip | "The site and goal the simulated visitor will attempt." |
| Simulated-user model knob tooltip | "Which AI model role-plays the simulated user." |
| Type chip tooltips (Likert/Single/Multi/Free) | "Rate on a 1–5 scale" / "Choose one option" / "Choose all that apply" / "Answer in their own words" |
| "Average rating" tile tooltip (survey) | "Average of the 1–5 ratings the persona gave across Likert questions." |
| "Complete/Incomplete" badge tooltip (survey) | "Complete means the persona answered every required question." |
| Need fit / Ease of use / Overall UX tile tooltips (web) | "How well the chosen item met the persona's need (0–10)." / "How easy the site was to use (0–10)." / "The visitor's overall experience rating (0–10)." |
| "Complete/Incomplete" badge tooltip (web) | "Complete means the run produced a full, usable result." |
| Instruments loading caption | "Loading questionnaires…" |
| Instruments error card | "We couldn't load the questionnaires. Check your connection and try again." |
| No-instrument preview placeholder | "Pick a questionnaire above to preview its questions." |
| Survey live-progress line | "Simulated user is answering…" (with "{answered} of {total} answered" under the bar) |
| Tasks loading caption | "Loading website tasks…" |
| Tasks error card | "We couldn't load the website tasks. Check your connection and try again." |
| WebsiteTaskCard helper (under eyebrow) | "This is the goal the simulated visitor will try to complete." |
| Web live-progress line | "Simulated visitor is browsing…" (with "Recorded {n} steps so far") |
| Empty trace row | "This run finished without recording any browser steps." |
| Screenshot fallback (alt + tile) | "Screenshot unavailable for this step." |
| Trace step action hint (from `summarizeAction`) | e.g. "Step 9 · clicked Add to cart" / "Step 3 · typed a search" |


---

# 05 · Runs — history, debrief & compare (option-aware)

Reskin of the Runs surface: the **history list**, the **run debrief** (option-aware: chatbot / survey / web), and the **side-by-side compare**. Pure in-place restyle — every hook, query key, route handler, narrowing helper, and prop signature stays. We swap the Executive-Precision / Material-3 token vocabulary for matrAIx tokens, swap Material Symbols for lucide, add the missing/empty UI states, and rewrite all copy to be friendly and tutorial-like.

**Files in scope**
- `src/components/RunsView.tsx` — list + sub-route switch (RunsView.tsx:43-360)
- `src/components/RunDetail.tsx` — single-run debrief (RunDetail.tsx:41-286)
- `src/components/RunCompare.tsx` — baseline-vs-candidate compare (RunCompare.tsx:46-470)
- `src/components/runsShared.tsx` — `DomainPill` / `SourceTag` / `GroundingChip` / `RecChip` + formatters
- `src/components/RatingChip.tsx` — the scannable score signature
- Reused, restyled in its own section: `src/components/cockpit/Scorecard.tsx` (chatbot scorecard) — token swap only, no structural change.

**Option-awareness, honestly scoped.** The detail/compare data layer is kept exactly as-is. Today `api.getPersonaEvalRun` returns the chatbot `PersonaEvalResult` (types.ts:463-474) and the chatbot path is fully wired. The survey and web debrief bodies specced below are **added UI states** that render the survey/web result shapes *already declared in the data layer* — `SurveyResult` (types.ts:525-540) and `WebResult` / `WebTrace` (types.ts:581-609). They activate when a loaded run carries an `applicationType` discriminator + the matching result object. This spec describes only the *rendering* of those shapes; it does not add, change, or propose new endpoints, queries, or types. Where the discriminator is read, treat it as "render whatever the data layer hands us," not a data-layer change.

---

## 1. Token & idiom migration (this surface's cheat-sheet)

Apply these substitutions everywhere in the five files. Per-component tables below only call out the non-obvious cases.

| Current (Executive Precision) | matrAIx | Notes |
|---|---|---|
| `bg-background` | `bg-surface-dim` | page scroll body |
| `bg-surface-container-lowest` (panels/cards) | `bg-surface` | the panel fill |
| `bg-surface-container-low` | `bg-surface-low` | sub-rows, header strips, inset rows |
| `bg-surface-container` / `bg-surface-container-high` | `bg-surface-high` | pills, tags, skeleton fill, avatar chips |
| `bg-field` | `bg-field` | unchanged; now used as the **progress-bar track** |
| `text-on-surface` | `text-text-main` | |
| `text-on-surface-variant` | `text-text-variant` | |
| `text-outline` | `text-text-dim` | quietest text/icons |
| `border-border-soft` / `border-outline-variant` | `border-outline` (dividers: `border-outline-dim`) | |
| `divide-border-soft` | `divide-outline` | |
| `text-primary` / `bg-primary` / `text-on-primary` | same names | cyan; CTA hover `hover:bg-primary-dim` |
| `bg-primary-container` (hover) | `bg-primary-dim` | |
| `bg-success*` / `text-on-success-container` (positive) | **`secondary` (mint)**: `bg-secondary` / `bg-secondary/10` / `text-secondary` / `border-secondary/30` | "good"/high/pass |
| `bg-warning*` / `text-warning` | `warn`: `bg-warn` / `bg-warn/10` / `text-warn` / `border-warn/30` | mid/caution |
| `bg-error*` / `text-error` / `border-error/40` | `danger`: `bg-danger` / `bg-danger/10` / `text-danger` / `border-danger/30` | low/fail/error |
| `text-display font-display` | `font-display text-[22px] font-bold tracking-tight` | page H1 |
| `text-headline-md font-headline-md` | `font-display text-[15px] font-semibold` | card H2 |
| `text-label-md font-label-md uppercase tracking-wider` | `.hud text-[9px]`/`text-[10px]` | micro-labels become real-word HUD labels |
| `font-mono-sm text-mono-sm` | `font-mono text-[11px]` (data) / `text-[10px]` (dense) | |
| `shadow-soft` / `shadow-sm` | *drop* | matrAIx is flat + bordered; reserve `.glow` for the single primary CTA only |
| `rounded-xl` | `rounded-md` | matrAIx panel radius; chips `rounded`/`rounded-sm` |
| `animate-rb-pulse` / `animate-rb-spin` | `animate-pulse` / `animate-spin` | |
| `FOCUS_RING` const | rely on the global `:focus-visible{outline:2px solid rgb(var(--primary));offset:2px}` (mockup line 48); keep the const name as an alias if cheaper, but it should resolve to the matrAIx ring | one focus treatment app-wide |

**Icons: `Sym` (Material Symbols) → lucide `<i data-lucide>`** (stroke-width 1.75, sized via `w-/h-`). The `Sym` call sites in these files map as:

| `Sym name` | lucide | `Sym name` | lucide |
|---|---|---|---|
| `arrow_back` | `arrow-left` | `arrow_forward` | `arrow-right` |
| `compare_arrows` | `git-compare` | `sort` | `arrow-down-narrow-wide` |
| `refresh` | `refresh-cw` | `check` | `check` |
| `history` | `history` | `play_arrow` | `play` |
| `error` | `alert-triangle` | `search_off` | `search-x` |
| `theater_comedy` | `drama` | `face` | `scan-face` |
| `smart_toy` | `bot` | `verified` | `badge-check` |
| `inventory_2` | `package` | `warning` | `triangle-alert` |
| `check_circle`/`cancel`/`remove_circle` | `check-circle`/`x-circle`/`minus-circle` | `help`/`help_outline` | `help-circle` |
| `fact_check` | `clipboard-check` | `activity` (new, run meta) | `activity` |

**Panel signature.** matrAIx runs cards are plain `bg-surface border border-outline rounded-md` (matching the mockup debrief, lines 355-425) — *not* the `.panel` corner-bracket, which the cockpit reserves for config panels. The one structural accent we keep is the **left rule on the lead score tile**: `border-l-4 border-l-<band>` where the band follows the score (mint/amber/danger), mirroring the mockup's `border-l-secondary` headline (line 355). Optionally apply `.panel` to the list table wrapper as the surface's quiet signature; keep it restrained.

**Theme toggle.** Runs has no color literals once migrated — every class above resolves through CSS vars, so light/dark "just works" off the global `#themeToggle` (mockup line 83) that the shell/design-system section owns. Acceptance check: grep these five files for `#`, `rgb(`, or any `*-container*`/`success`/`error`/`warning` class — there should be zero after the swap.

---

## 2. Score colour scale → matrAIx (required mapping)

The red→amber→green→mint scale lives in one place — `scoreBand()` + `SCORE_BAND_CLASS` in `cockpit/cockpitShared.tsx:315-334`. **Thresholds and the `scoreBand` function are unchanged** (high ≥0.7, mid ≥0.4, low <0.4, null→none). Only the class strings are retoned. High uses **mint (secondary)** per the design ("mint for high"); the cyan `primary` is never used to express a score.

| Band | normalized | current `{text, bar, soft}` | **matrAIx `{text, bar, soft}`** |
|---|---|---|---|
| high | ≥ 0.7 | on-success-container / success / success-container | **`text-secondary` / `bg-secondary` / `bg-secondary/10`** |
| mid | ≥ 0.4 | on-warning-container / warning / warning-container | **`text-warn` / `bg-warn` / `bg-warn/10`** |
| low | < 0.4 | on-error-container / error / error-container | **`text-danger` / `bg-danger` / `bg-danger/10`** |
| none | null/NaN | on-surface-variant / outline-variant / surface-container-high | **`text-text-dim` / `bg-outline` / `bg-surface-high`** |

Progress-bar **track** changes from `bg-surface-container-high` to **`bg-field`** (mockup uses `bg-field` tracks, lines 371-372). The `border-l-4` lead-tile accent reads the band's `bg-*` colour (mint/amber/danger).

Consumers needing no further change once the table above is applied: `RatingChip` (RatingChip.tsx:30-31,48), `Scorecard` criterion bars + overall number (Scorecard.tsx:57,151), and the Compare delta tints (see §5, which switch to the same secondary/danger pair).

---

## 3. Runs list — `RunsView.tsx`

Calm, scannable table; the only loud element stays the `RatingChip`. Layout/grid and the compare-pick state machine are untouched — class swap + copy + an option-type column.

### 3.1 Chrome & header (RunsView.tsx:102-166)

| Element | current | target matrAIx | notes |
|---|---|---|---|
| Scroll container :103 | `overflow-auto bg-background` | `overflow-auto bg-surface-dim custom-scrollbar` | add thin scrollbar |
| Width wrap :104 | `max-w-[1100px] px-lg py-7` | `max-w-[1180px] px-6 py-7` | match mockup gutter (line 341) |
| Title :115 | `text-display font-display text-on-surface` "Runs" | `font-display text-[22px] font-bold tracking-tight` + a `hud text-[10px] text-primary` eyebrow "PersonaEval · Runs" above it | mockup H1 idiom (line 343) |
| Count :117 | `font-mono-sm text-on-surface-variant` | `font-mono text-[11px] text-text-dim` | |
| Back-to-cockpit btn :110 | outline button, `Sym arrow_back` | `rounded-md border border-outline bg-surface-low px-3 py-1.5 text-[12px] text-text-variant hover:border-primary hover:text-text-main` + `arrow-left` | |
| Compare toggle :128-132 | active `bg-primary text-on-primary shadow-sm hover:bg-primary-container` / inactive outline | active `bg-primary text-on-primary hover:bg-primary-dim` / inactive outline (as back btn) + `git-compare` | drop shadow |
| Refresh btn :142 | outline + `refresh` spin | same outline idiom + `refresh-cw`, spinner `animate-spin` | |
| Compare hint banner :150 | `rounded-lg border border-primary/30 bg-primary/5` | `rounded-md border border-primary/30 bg-primary/10` + `git-compare` `text-primary` | copy → §9 |

### 3.2 Table (RunsView.tsx:205-290)

| Element | current | target matrAIx |
|---|---|---|
| Wrapper :207 | `rounded-xl border border-border-soft bg-surface-container-lowest shadow-soft` | `rounded-md border border-outline bg-surface overflow-hidden` (optionally add `panel`) |
| Header row :210 | `bg-surface-container-low ... text-[10.5px] uppercase tracking-[0.04em] text-on-surface-variant` | `bg-surface-low border-b border-outline` + each label as `hud text-[9px] text-text-dim` |
| Row list :221 | `divide-y divide-border-soft` | `divide-y divide-outline-dim` |
| Row button :232-234 | hover `hover:bg-surface-container-low`; picked `bg-primary/5`; disabled `opacity-45` | hover `hover:bg-surface-low`; picked `bg-primary/10`; disabled `opacity-45` |
| Selection box :240-244 | picked `border-primary bg-primary text-on-primary` / idle `border-outline-variant bg-surface-container-lowest` | picked same / idle `border-outline bg-surface-lowest` + `check` |
| Persona name :258 | `text-body-md font-medium text-on-surface` | `text-[13px] font-medium text-text-main` |
| mono cols (Turns/When) :275,280 | `font-mono-sm text-on-surface-variant` | `font-mono text-[11px] text-text-variant tabular-nums` |

### 3.3 Option-type column (forward-compatible)

Add one column between Rating and Persona: a small **app-type tag** so a mixed list reads at a glance. It renders from whatever type the summary carries (chatbot today); absent → defaults to chatbot. New atom `AppTypeTag` in `runsShared.tsx`, same idiom as `DomainPill`:

| type | icon (lucide) | label |
|---|---|---|
| chatbot | `message-square` | Chatbot |
| survey | `clipboard-check` | Survey |
| web | `globe` | Web |

`inline-flex items-center gap-1 rounded border border-outline bg-surface-high px-1.5 py-0.5 text-[11px] text-text-variant`. The grid template (RunsView.tsx:202-203) gains one `64px` column; header gains a `Kind` HUD label. The `Rating` column header keeps showing `RatingChip` (chatbot overall/10); for survey/web summaries that arrive later it shows the option's headline figure (mean-Likert /5, overall-UX /10) via the same chip — no new logic, just the value the summary provides.

---

## 4. Run debrief — `RunDetail.tsx` (OPTION-AWARE)

The debrief reorganizes to the mockup's "Run debrief" shape (lines 340-429): a one-line **run-meta breadcrumb**, a **headline score band + metric tiles**, then the body. Branch on the loaded run's `applicationType`; the chatbot branch is the current `RunDetailBody` restyled, survey/web are added branches.

### 4.0 Shared chrome (all options)

| Element | current (RunDetail.tsx) | target matrAIx |
|---|---|---|
| Container :50 | `overflow-auto bg-background`, wrap `max-w-[860px] px-lg py-6` | `overflow-auto bg-surface-dim custom-scrollbar`, wrap `max-w-[1240px] px-6 py-7` (debrief is wider, two-col) |
| Back button :224-234 | outline `Sym arrow_back` "Runs" | outline idiom + `arrow-left`; copy "All runs" (mockup line 343) |
| **Run-meta line** (replaces dense header :81-103) | header card with name/source/domain/grounding/rating + meta row | one `hud text-[9px] text-text-dim flex items-center gap-2` line led by `activity`/`clipboard-check`/`globe`, e.g. *Chatbot run · RecAI on the movie catalog · persona "Financial Manager" · Jun 26, 14:30* (line 353). `RatingChip`/`GroundingChip` move into the headline band below. |

The page H1 is `font-display text-[22px] font-bold` "Run debrief"; the chatbot/survey/web body chooses its own headline band.

### 4.1 Chatbot debrief

Restyle of the existing `RunDetailBody` (RunDetail.tsx:72-150). Header card → meta line + headline band; Trajectory and Scorecard sections keep their structure.

**Headline band** (replaces the inline overall in the old header):
- Lead tile (`lg:col-span-4`): `bg-surface border border-outline border-l-4 border-l-<band> rounded-md p-5`; `hud text-[10px] text-<band>` "Overall satisfaction"; number `font-display text-[44px] font-bold leading-none text-<band>` + `text-text-dim text-[13px]` "/ 10"; rationale `text-[12px] text-text-variant leading-relaxed mt-4` (from `questionnaire.ratingReason`). `<band>` = `scoreBand(overall/10)`'s colour (mockup line 355 shows the mint/high case).
- Three metric tiles (`lg:col-span-8 grid grid-cols-3`): `bg-surface border border-outline rounded-md p-4`; `hud text-[9px] text-text-dim` caption; `font-display text-[26px] font-bold` value. Captions (friendly, §9): "Turns before first suggestion" (`turnsToRecommendation`), "Total turns" (`numTurns`), "Items suggested" (`recommendedItemCount`). The old `MetricTile` (Scorecard.tsx:203) folds into these — keep one tile component, restyle.
- `GroundingChip` sits under the lead tile (`mt-1.5`), retoned (§6).

**Transcript & trace** (RunDetail.tsx:106-121, 153-204) — left `lg:col-span-7`:

| Element | current | target matrAIx |
|---|---|---|
| Section label :107 | `text-label-md uppercase` "Trajectory" | `hud text-[10px] text-primary` "Transcript & trace" |
| Turn card :157 | `rounded-xl border border-border-soft bg-surface-container-lowest p-4 shadow-soft` | `bg-surface border border-outline rounded-md p-5 space-y-6` (one card holds the turns, mockup line 364) |
| Persona avatar :168 | `bg-primary/10` + `face` | `w-8 h-8 rounded bg-primary/10 border border-primary/25` + `scan-face text-primary`; bubble `bg-primary/5 border border-outline rounded p-3.5` (line 365) |
| Persona label :171 | `text-label-md` "Persona" | `hud text-[9px] text-primary` "Persona" + `hud text-[9px] text-text-dim` "turn N" |
| RecBot avatar :181 | `bg-surface-container-high` + `smart_toy` | `bg-surface-high border border-outline` + `bot text-text-variant`; row `flex-row-reverse`; bubble `bg-surface-low border border-outline rounded p-3.5` (line 366) |
| Agent label :184 | "RecBot" | `hud text-[9px] text-text-variant` with the **app's** name (RecAI / OpenBB / Medical), not a hard-coded "RecBot" — read from config; copy §9 |
| Hiccup line :187 | `text-error italic` | `text-danger italic text-[13px]` |
| `RecChip` row :194 | see §6 | retoned chip |
| `DecisionTag` :207-217 | `bg-success-container`/`bg-warning-container` | `text-secondary border border-secondary/30 bg-secondary/10` (satisfied) / `text-warn border border-warn/30 bg-warn/10` (gave up), `hud text-[9px]` |

**Self-report scorecard** (reuses `Scorecard`, RunDetail.tsx:124-137) — right `lg:col-span-5`. Token swap only (§2 + §2's score table); structure preserved:

| Scorecard element | current | target matrAIx |
|---|---|---|
| Card :61 / header :63 | rounded-xl + container header | `bg-surface border border-outline rounded-md`; header `bg-surface-low border-b border-outline`, title `hud text-[10px] text-primary` "Self-report scorecard" |
| Overall number :79 | `text-[40px] font-bold ${overallColor.text}` | `font-display text-[44px] font-bold` band colour (now shown in §4.1 headline band — Scorecard's own overall block may be hidden in the debrief to avoid duplication; keep it in the cockpit) |
| Criterion bar track :171 | `bg-surface-container-high` | `bg-field` |
| Criterion rows :102-113 | "Constraint satisfaction" / "Preference satisfaction" | relabel (§9) + bar/score band colour from §2 |
| Clarifying line :180-199 | success-container vs container | mint pass `border-secondary/30 bg-secondary/10 text-secondary` / neutral `border-outline bg-surface-low`; copy §9 |

### 4.2 Survey debrief (added body — reads `SurveyResult`, types.ts:525-540)

No environment/transcript. Mirrors mockup lines 379-404.

| Block | structure | data |
|---|---|---|
| Stat tiles (`grid grid-cols-2 sm:grid-cols-4 gap-5`) | four `bg-surface border border-outline rounded-md p-4`; lead tile `border-l-4 border-l-<band>` | **Questions answered** `numAnswered/numQuestions` (`font-display text-[26px]`); **Answers look valid** → mint `Valid` / danger `Needs review` badge from `completion.valid`; **Average agreement** `meanLikert` `x.x` + `text-text-dim /5`; **Written answers** = count of `free_text` answers |
| Answers list (`lg:col-span-7`) | label `hud text-[10px] text-primary` "Answers"; card `bg-surface border border-outline rounded-md divide-y divide-outline-dim`; each row `p-4`: `text-[12px] font-medium` "Qn · {prompt}" + right-aligned value (`font-mono text-[12px]`, Likert scored `x / 5` in band colour, choice as text, free-text tagged `free text` in `text-text-dim`); `text-[11px] text-text-dim` "Rationale: …" + `text-text-variant` "conf 0.NN" when `answer.confidence` present | `answers[]` (types.ts:510-515) joined to `instrument.questions` for prompt/type |
| Trajectory (`lg:col-span-5`) | label `hud text-[10px] text-primary` "Trajectory"; card `bg-surface border border-outline rounded-md p-4 font-mono text-[11px] leading-relaxed space-y-2`; each event `flex gap-2.5`: `text-text-dim` time · `text-primary` action · `text-text-variant` detail; the `submit` event in `text-secondary font-bold` | `trajectory[]` (types.ts:517-523) |

### 4.3 Web debrief (added body — reads `WebResult` + `WebTrace`, types.ts:581-609)

Mirrors mockup lines 406-428.

| Block | structure | data |
|---|---|---|
| UX score tiles (`lg:col-span-5 grid grid-cols-3`) | three `bg-surface border border-outline rounded-md p-4`; lead `border-l-4 border-l-<band>` | **Met the persona's need** `needSatisfaction`/10; **Ease of use** `easeOfUse`/10; **Overall experience** `overallExperienceRating`/10 — each `font-display text-[24px] font-bold` + `text-text-dim /10`; band colour = `scoreBand(value/10)` |
| Selected product (`lg:col-span-7`) | `bg-surface border border-outline rounded-md p-5 flex items-center gap-4`; icon tile `bg-surface-high border border-outline` + `package text-primary`; name `text-[14px] font-semibold` + mint/danger `Valid`/`Invalid` badge from `valid`; `font-mono text-[10px] text-text-dim` SKU/price if present; `text-[11px] text-text-variant` reason | `selectedProductName`, `valid`, `reason` |
| Browser trace | label `hud text-[10px] text-primary flex items-center gap-2` + `footprints` "Browser trace · {events.length} steps"; grid `grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3`; each step card `bg-surface border border-outline rounded-md overflow-hidden`: `aspect-video bg-surface-low border-b border-outline` screenshot (`<img src={screenshotUrl}>` when present, else `image` lucide placeholder `grid place-items-center text-text-dim`), caption `p-2.5` with `hud text-[8px] text-text-dim` "Step N · {action}" + `font-mono text-[10px] text-text-variant truncate` action detail | `trace.events[]` (types.ts:597-604): `step`, `message`, `screenshotUrl`, `actions[0].name` |

Screenshots are honest: render the real `screenshotUrl`; the lucide `image` tile is only the fallback when a step has none.

---

## 5. Compare — `RunCompare.tsx`

Baseline-anchored side-by-side. Logic (delta math RunCompare.tsx:108-113, ordering :168-170, config diffs :414-428) is untouched — token swap + option-aware dimension set + delta retone.

### 5.1 Chrome, headers, config (RunCompare.tsx:62-203)

| Element | current | target matrAIx |
|---|---|---|
| Container :63-64 | `bg-background`, `max-w-[1000px] px-lg py-6` | `bg-surface-dim custom-scrollbar`, `max-w-[1180px] px-6 py-7` |
| Title :74 | `text-display font-display` "Compare runs" | `font-display text-[22px] font-bold` + `hud text-[10px] text-primary` eyebrow "PersonaEval · Compare" |
| `SideHeader` :261 | `rounded-xl ... bg-surface-container-lowest shadow-soft` | `bg-surface border border-outline rounded-md p-4`; **baseline** keeps neutral, **candidate** gets `border-l-4 border-l-primary` |
| Role badge :264-266 | baseline `bg-surface-container`; candidate `bg-primary/10 text-primary` | baseline `bg-surface-high text-text-variant`; candidate `bg-primary/10 text-primary`, both `hud text-[9px]`; labels → "Baseline" / "Candidate (read against baseline)" (§9) |
| Config panel :183-203 | rounded-xl card; "Configuration" | `bg-surface border border-outline rounded-md p-4`; `hud text-[10px] text-primary` "What changed between the two"; diff rows `arrow-right` glyph |

### 5.2 Score deltas (RunCompare.tsx:205-338)

| Element | current | target matrAIx |
|---|---|---|
| Panel :206 | rounded-xl card | `bg-surface border border-outline rounded-md p-4` |
| Section label :208 | "Scores · candidate vs baseline" | `hud text-[10px] text-primary` "How the candidate scored vs the baseline" |
| Regression count :211 | `{n} regression(s)` | `hud text-[9px] text-text-variant` "{n} scores dropped" (singular "1 score dropped") |
| Order toggle :214-226 | active `bg-primary text-on-primary` + `sort` | same active; inactive outline idiom + `arrow-down-narrow-wide`; label "Show biggest drops first" |
| Column header :230 | `text-[10.5px] uppercase` | `hud text-[9px] text-text-dim`; labels "Dimension / Baseline / Candidate / Change" |
| `DeltaRow` bars :314-318 | track `bg-surface-container-high`; baseline `bg-outline-variant`; candidate `bg-primary` | track `bg-field`; baseline `bg-outline`; candidate `bg-primary` |
| Delta tint :299-303 | up `success-container`; down `error-container`; flat `surface-container` | **up `text-secondary bg-secondary/10`**; **down `text-danger bg-danger/10`**; flat `text-text-variant bg-surface-high`; arrows `arrow-up`/`arrow-down`/`minus` |

### 5.3 Option-aware dimensions

`improvement()` and `DeltaRow` are unchanged; only the `dimensions` array (RunCompare.tsx:133-165) becomes keyed by the runs' shared `applicationType` (compare pairs same-type runs; the list only lets two runs of one kind be picked — note for §3 selection):

- **chatbot** (today): Overall satisfaction /10, Stayed within my requirements /5, Matched my preferences /5, Turns before first suggestion (`lowerIsBetter`), Items suggested. (Labels = the friendly rewrites; same fields as :135-164.)
- **survey**: Average agreement /5, Questions answered (n/total), Answers valid (1/0). From `SurveyCompletion`.
- **web**: Met the persona's need /10, Ease of use /10, Overall experience /10. From `WebResult`.

### 5.4 Aligned trajectories (RunCompare.tsx:344-401)

| Element | current | target matrAIx |
|---|---|---|
| Wrapper :358 | `rounded-xl ... bg-surface-container-lowest shadow-soft` | `bg-surface border border-outline rounded-md overflow-hidden` |
| Side labels :360-366 | `gap-px bg-border-soft`, cells `bg-surface-container-low` `text-[10.5px] uppercase` | `gap-px bg-outline`, cells `bg-surface-low` `hud text-[9px] text-text-dim` "Baseline · {domain}" / "Candidate · {domain}" |
| Rows :370 | `gap-px bg-border-soft` | `gap-px bg-outline-dim` |
| `TurnCell` :381-400 | cells `bg-surface-container-lowest`; placeholder `text-outline italic`; hiccup `text-error` | `bg-surface`; placeholder `text-text-dim italic` "turn N didn't happen"; hiccup `text-danger`; "Turn N" → `hud text-[9px]` |

For survey/web compares, this section swaps to an aligned **answers** diff (survey) or **step list** (web) using the same two-column `divide`/`gap-px` idiom; chatbot keeps the per-turn transcript.

---

## 6. Shared atoms — `runsShared.tsx` & `RatingChip.tsx`

| Atom | current | target matrAIx |
|---|---|---|
| `DomainPill` :158-163 | `border-border-soft bg-surface-container text-on-surface-variant` | `border border-outline bg-surface-high text-text-variant text-[11px] rounded` |
| `SourceTag` :167-173 | `bg-surface-container text-[10.5px] text-on-surface-variant` | `bg-surface-high text-text-dim font-mono text-[10px] rounded` |
| `GroundingChip` :182-208 | grounded `bg-success-container text-on-success-container`; ungrounded `bg-warning-container text-warning` | grounded `text-secondary border border-secondary/30 bg-secondary/10` + `package`; ungrounded `text-warn border border-warn/30 bg-warn/10` + `triangle-alert`; copy §9 |
| `RecChip` :211-217 | `border-border-soft bg-surface-container-lowest` | `border border-outline bg-surface-low`; id `font-mono text-[10px] text-text-dim`, title `text-text-variant` |
| `RatingChip` none :37 | `border-border-soft bg-surface-container text-on-surface-variant` "—" | `border border-outline bg-surface-high text-text-dim` |
| `RatingChip` scored :48 | `${color.text} ${color.soft}` | unchanged code; resolves to §2 mint/amber/danger; "/10" suffix kept |
| `AppTypeTag` (new) :§3.3 | — | `border border-outline bg-surface-high text-text-variant text-[11px]` + per-type lucide |

`fmtRunDate`, `fmtDomain`, `fmtSource`, `fmtGoalContext`, `GOAL_CONTEXT_LABELS` (runsShared.tsx:89-151) are formatters — keep, but extend `GOAL_CONTEXT_LABELS` copy per §9.

---

## 7. UI states (restyle + the additions)

Reuse the mockup state idioms (lines 569-709): a dashed icon tile for empty, `animate-pulse` skeletons, a `border-l-4 border-l-danger` panel + danger button for errors, `border-l-warn` for offline.

| State | location | target matrAIx |
|---|---|---|
| List loading :296-312 | grey skeleton rows | rows of `animate-pulse` blocks on `bg-surface-high`, wrapper `bg-surface border border-outline rounded-md` |
| **List empty** :314-335 | "No runs yet" card | dashed tile `w-14 h-14 rounded-md bg-surface-high border border-dashed border-outline` + `history text-text-dim`; `font-display font-semibold text-[15px]` heading; friendly body; primary CTA `bg-primary text-on-primary glow` + `play` (§9) |
| List error :337-358 | `border-error/40 bg-error-container/40` | `bg-surface border border-outline border-l-4 border-l-danger rounded-md`; icon tile `bg-danger/10 border border-danger/30` + `alert-triangle text-danger`; retry `border border-danger/40 bg-danger/10 text-danger hover:bg-danger/20` + `refresh-cw` |
| Detail loading :237-245 | pulse blocks | `animate-pulse` on `bg-surface-high` |
| Detail not-found :247-259 | `search_off` card | dashed tile + `search-x`; copy §9 |
| Detail error :261-284 | error card | danger panel idiom (as list error) |
| Compare loading/error :435-468 | pulse / error card | same idioms |
| **Trajectory empty** (RunDetail.tsx:110-113) | "This run has no recorded turns." | dashed `bg-surface-low` note; copy §9 |
| **No evaluation** (RunDetail.tsx:133-137) | "finished without a recorded evaluation" | dashed note; copy §9 |
| **Survey/web empties** (new) | — | "No answers were recorded." / "No browser steps were captured for this run." in the same dashed-note idiom |
| Aligned-traj empty (RunCompare.tsx:349-355) | "Neither run recorded any turns." | dashed note; copy §9 |

---

## 8. Copy rewrites

All user-facing strings on this surface, rewritten friendly + tutorial. Location is `file:line`.

| Location | Current | Friendly rewrite |
|---|---|---|
| RunsView.tsx:115 | `Runs` | `Runs` (+ eyebrow `PersonaEval · Runs`) |
| RunsView.tsx:118-119 | `{n} run` / `{n} runs` | `1 saved run` / `{n} saved runs` |
| RunsView.tsx:113 | `Cockpit` (back) | `Back to cockpit` |
| RunsView.tsx:135 | `Compare` / `Cancel compare` | `Compare two runs` / `Cancel` |
| RunsView.tsx:145 | `Refreshing…` / `Refresh` | `Checking for new runs…` / `Refresh` |
| RunsView.tsx:153-154 | `Pick two runs — the first is the baseline. {n}/2 selected` | `Pick two runs to compare. The first one you choose is the baseline; the second is measured against it. ({n} of 2 chosen)` |
| RunsView.tsx:162 | `Compare 2 runs` | `Compare these two` |
| RunsView.tsx:217 | header `Rating` | `Score` |
| RunsView.tsx:218 | `Persona` | `Simulated user` |
| RunsView.tsx:217 (new) | — | `Kind` (app-type column) |
| RunsView.tsx:219 | `Goal context` | `Conversation style` |
| RunsView.tsx:220 | `Turns` | `Turns` |
| RunsView.tsx:221 | `When` | `When` |
| RunsView.tsx:259 | `Unnamed persona` | `Unnamed persona` |
| RunsView.tsx:320 | `No runs yet` | `No saved runs yet` |
| RunsView.tsx:321-324 | `Launch a PersonaEval run from the cockpit. Completed runs land here, newest first — ready to open or compare side by side.` | `Once you run a simulation, it's saved here so you can reopen it, read the full transcript and scores, or compare two runs side by side. Head to the cockpit to start your first one.` |
| RunsView.tsx:331 | `Go to the cockpit` | `Start your first run` |
| RunsView.tsx:344 | `Couldn't load runs` | `We couldn't load your runs` |
| RunsView.tsx:338 | `The runs list could not be loaded.` | `Something went wrong fetching your saved runs. This is usually a brief connection hiccup.` |
| RunsView.tsx:353 | `Try again` | `Try again` |
| RunDetail.tsx (H1) | — | `Run debrief` |
| RunDetail.tsx:233 | `Runs` (back) | `All runs` |
| RunDetail.tsx (meta, new) | derived header | `Chatbot run · {App} on the {domain} catalog · persona "{name}" · {date}` (survey: `Survey run · {instrument} · …`; web: `Web run · {task} on {site} · …`) |
| RunDetail.tsx:108 | `Trajectory` | `Transcript & trace` |
| Headline lead tile (new) | overall number | label `Overall satisfaction`; below: `How the simulated user rated the experience, out of 10.` |
| metric tiles (Scorecard.tsx:126,128,129) | `Turns to first rec` / `Turns` / `Items recommended` | `Turns before first suggestion` / `Total turns` / `Items suggested` |
| Scorecard.tsx:103 | `Constraint satisfaction` | `Stayed within my requirements` |
| Scorecard.tsx:108 | `Preference satisfaction` | `Matched my preferences` |
| Scorecard.tsx:66 | `Evaluation` (title) | `Self-report scorecard` |
| Scorecard.tsx:84 | `Persona self-rating` | `The simulated user's own rating` |
| Scorecard.tsx:194-197 | `Clarifying questions — asked useful ones / none asked` | `Asked helpful follow-up questions — yes, it did` / `Asked helpful follow-up questions — none this time` |
| RunDetail.tsx:184 | `RecBot` | the app's real name: `RecAI` / `OpenBB` / `Medical assistant` |
| RunDetail.tsx:171 | `Persona` | `Simulated user` |
| RunDetail.tsx:188-189 | `RecBot did not return a reply for this turn.` | `The app didn't reply on this turn (it may have hit an error).` |
| RunDetail.tsx:212 | `satisfied` / `gave up` | `Got what they needed` / `Gave up` |
| RunDetail.tsx:111-112 | `This run has no recorded turns.` | `No conversation turns were recorded for this run.` |
| RunDetail.tsx:135 | `This run finished without a recorded evaluation.` | `This run finished before a score was produced — there's no scorecard to show.` |
| RunDetail.tsx:253-256 | `Run not found` / `This run may have been removed. Head back to the list to pick another.` | `We couldn't find this run` / `It may have been deleted. Go back to the list to pick another.` |
| RunDetail.tsx:270-271 | `Couldn't load this run` / `This run could not be loaded.` | `We couldn't open this run` / `Something went wrong loading the details. Try again in a moment.` |
| runsShared.tsx:205 | `{n} grounded` | `{n} from the real catalog` |
| runsShared.tsx:205 | `Ungrounded` | `Nothing from the catalog` |
| runsShared.tsx:199-202 (tooltip) | `No catalog items recommended — the agent's suggestions aren't grounded in the corpus (base knowledge)` | `The app suggested items but none came from the real product catalog — they're from the model's own knowledge, so treat them with care.` |
| runsShared.tsx:131-134 | `curated` (source fallback) | `curated` |
| runsShared.tsx:141-144 | `scenario_default → Realistic scenario`, `gradual_reveal → Gradual reveal` | keep labels; tooltip `Realistic scenario`: `The user reveals their needs naturally, like a real conversation.` / `Gradual reveal`: `The user shares their needs a little at a time.` |
| RunCompare.tsx:74 | `Compare runs` | `Compare two runs` |
| RunCompare.tsx:268 | `Baseline` | `Baseline` |
| RunCompare.tsx:268 | `Candidate` | `Candidate (measured against the baseline)` |
| RunCompare.tsx:185 | `Configuration` | `What changed between the two` |
| RunCompare.tsx:188-189 | `Same domain, goal context, and persona source on both sides.` | `Both runs used the same settings — domain, conversation style, and persona source all match.` |
| RunCompare.tsx:209-210 | `Scores · candidate vs baseline` | `How the candidate scored vs the baseline` |
| RunCompare.tsx:212-213 | `{n} regression(s)` | `{n} scores dropped` / `1 score dropped` |
| RunCompare.tsx:225 | `Order by regressions` | `Show biggest drops first` |
| RunCompare.tsx:231-234 | `Dimension / Baseline / Candidate / Delta` | `What we measured / Baseline / Candidate / Change` |
| RunCompare.tsx:136-160 (dims) | `Overall rating / Constraint satisfaction / Preference satisfaction / Turns to first rec / Items recommended` | `Overall satisfaction / Stayed within my requirements / Matched my preferences / Turns before first suggestion / Items suggested` |
| RunCompare.tsx:247 | `Trajectories · aligned per turn` | `The two conversations, turn by turn` |
| RunCompare.tsx:362-365 | `Baseline · {domain}` / `Candidate · {domain}` | unchanged (clear already) |
| RunCompare.tsx:383 | `no turn {n}` | `turn {n} didn't happen` |
| RunCompare.tsx:393 | `RecBot did not return a reply.` | `The app didn't reply here.` |
| RunCompare.tsx:351-354 | `Neither run recorded any turns.` | `Neither run recorded a conversation.` |
| RunCompare.tsx:454-455 | `Couldn't load the comparison` / `One of the runs could not be loaded.` | `We couldn't load the comparison` / `One of the two runs wouldn't load. Try again in a moment.` |

**New survey/web debrief copy** (added bodies):

| Location | Friendly text |
|---|---|
| Survey tile captions | `Questions answered` / `Answers look valid` / `Average agreement (1–5)` / `Written answers` |
| Survey validity badge | `Valid` / `Needs review` |
| Survey answer rationale | `Why: {rationale}` · confidence chip `How sure: {0.NN}` |
| Survey answers empty | `No answers were recorded for this survey run.` |
| Web tile captions | `Met the persona's need` / `Ease of use` / `Overall experience` (each `out of 10`) |
| Web product badge | `Valid pick` / `Invalid pick` |
| Web product reason | `Why this one: {reason}` |
| Web trace heading | `Browser trace · {n} steps` |
| Web step caption | `Step {n} · {action}` |
| Web trace empty | `No browser steps were captured for this run.` |
| Web screenshot fallback (alt) | `Screenshot not available for this step` |

**New helper / tooltip / first-run tutorial hints:**

- **List header sub-hint** (under the title, first visit): `Each row is one simulation. Click it to read the full transcript and scores, or turn on Compare to put two side by side.`
- **Score column tooltip:** `The simulated user's overall rating, out of 10. Green is great, amber is mixed, red means it fell short.`
- **Kind column tooltip:** `Which kind of app was tested — a chatbot, a survey, or a website.`
- **Compare-mode first hint** (banner, §8 row): teaches baseline-vs-candidate as above.
- **Grounding chip** (already a tooltip, §8): teaches "from the real catalog" vs "model's own knowledge."
- **Delta legend** (Compare scores panel, small `hud text-[9px] text-text-dim`): `Green = the candidate did better · red = it did worse · grey = no change. For "turns before first suggestion," fewer turns is better.`
- **Debrief intro line** (under H1, per option): chatbot `A simulated user chatted with the app for a few turns, then rated how well it understood and met their needs.` · survey `A simulated user filled out this questionnaire; here are their answers and how complete they were.` · web `A simulated user browsed the site to finish a task — here are the UX ratings and a replay of every step they took.`


---

# 06 · Persona catalog + cross-cutting (states · responsive · a11y)

Scope: the ⌘K item-catalog palette (`src/components/CatalogDrawer.tsx`), the persona-catalog rail
(`src/components/cockpit/PersonaCatalog.tsx`) and its cards (`PersonaCard.tsx`), the persona detail
drawer (`PersonaDrawer.tsx`), then the cross-cutting rules every section inherits: the standard
state set, responsive/mobile behaviour, and accessibility.

This is an **in-place reskin**. Keep every hook, query, parser, prop, and DOM affordance exactly as
it is today (focus traps, `aria-*`, debounce, `placeholderData`, `useQuery` keys). We only swap design
tokens, re-arrange a few classNames, add the theme-aware focus offset, add the missing states, and
rewrite copy. **No data-layer change.** Where the mockup shows fields the backend does not return,
we render-if-present and degrade honestly — never fabricate.

---

## 0. Token translation key (Executive Precision → matrAIx)

The current files use the old token names. Apply this key everywhere below so the per-component
tables can stay terse. Class *names* like `bg-primary`/`text-on-primary` are reused; only their
token *values* change (indigo → cyan) and are owned by the design-system section.

| Current (Executive Precision) | matrAIx target | Role |
|---|---|---|
| `bg-background` | `bg-surface-dim` | page background |
| `bg-surface-container-lowest` (rails, drawers, insets) | `bg-surface-lowest` | rail / drawer / inset |
| `bg-surface-container-low` | `bg-surface-lowest` | left-rail body |
| panel surface | `bg-surface` + `border border-outline rounded-md` (+ `.panel` for the corner accent) | panel / card |
| input inner surface | `bg-field` | text inputs |
| `bg-surface-container` (chips / inactive) | `bg-surface-low` | inactive chip / pill |
| `bg-surface-container-high` · `-highest` | `bg-surface-high` | skeleton fill · avatar · hover |
| `bg-surface-variant` (row hover) | `bg-surface-high` | row hover |
| `border-border-soft` | `border-outline` (faint hairlines `border-outline-dim`) | borders / dividers |
| `border-outline-variant` | `border-outline` | control borders |
| `text-on-surface` | `text-text-main` | primary text |
| `text-on-surface-variant` | `text-text-variant` | secondary text |
| `text-outline` | `text-text-dim` | placeholder / quiet meta |
| `text-primary` · `bg-primary` · `text-on-primary` | same names (now cyan) | accent · primary CTA |
| success: `text-on-success-container` · `bg-success` · `bg-success-container` | mint: `text-secondary` · `bg-secondary` · `bg-secondary/10` + `border-secondary/30` | positive / done |
| error: `text-error` · `bg-error` · `bg-error-container` · `border-error/40` | `text-danger` · `bg-danger` · `bg-danger/10` · `border-danger/30` | error |
| warning: `text-warning` · `bg-warning-container` | `text-warn` · `bg-warn/10` + `border-warn/30` | warning |
| `shadow-pop` (drawers / popovers) | `shadow-2xl` | overlays |
| `shadow-soft` (selected card) | drop it — express selection with `border-primary` + `.panel` | flat by default |
| heading `text-headline-* font-headline-* uppercase tracking-*` | eyebrow `.hud text-[10px] text-primary` + title `font-display font-bold` | headings |
| `font-mono-sm text-mono-sm` | `font-mono text-[10px]` / `text-[11px]` | mono data / ids |
| `text-body-md` · `text-body-sm` | `text-[13px]` · `text-[12px]` | body |
| `text-label-md font-label-md` | `.hud text-[9px]` (micro-label) or `text-[11px]` (control) | labels |
| `animate-rb-pulse` · `animate-rb-spin` | `animate-pulse` · `animate-spin` | skeleton · spinner |
| `Sym name="…"` (Material Symbols) | lucide glyph (see icon note) | icons |

**Icon note (cross-cutting):** matrAIx draws icons via **lucide**. Whether to retire the shared
`Sym` Material-Symbols component (`cockpitShared.tsx:55`) for lucide is owned by the design-system /
shell section. Tables below name the **lucide** glyph the mockup uses with the current `Sym`
ligature in parentheses, e.g. `scan-face` (Sym `person`). If `Sym` is kept, use the parenthetical
ligature; the intent is identical.

**Focus-ring token (one shared string):** `FOCUS_RING` at `cockpitShared.tsx:30` ends in
`ring-offset-surface-container-lowest`. Retarget the offset to the matrAIx page/inset token
(`ring-offset-surface-dim`, or `ring-offset-surface-lowest` inside rails/drawers) so the 2px cyan
ring reads in both themes. This is the single edit that fixes focus visibility app-wide; coordinate
with the design-system section so it changes once.

---

## 1. ⌘K command palette — item catalog · `CatalogDrawer.tsx`

The ⌘K / "Search catalog" palette (opened in `App.tsx:250`, top-bar button `TopBar.tsx:70`) searches
the **RecAI recommendation corpus** (items: title / year / genre / id), not personas. Keep all of
it — debounce (`:113`), `useQuery` (`:129`), expand-on-click rows, Escape-to-close (`:119`). Reskin
only: right-anchored slide-over on a scrim.

| Element (file:line) | Current | matrAIx target | Notes |
|---|---|---|---|
| Scrim (`:143`) | `bg-[oklch(0.3_0.03_280/.28)] backdrop-blur-[1px]` | `bg-black/50 backdrop-blur-sm` | matches mockup drawer backdrop (`app-redesign-v3.html:893`) |
| Panel (`:150`) | `w-[460px] border-l border-border-soft bg-surface-container-low shadow-pop` | `w-[460px] max-w-[92vw] border-l border-outline bg-surface-lowest shadow-2xl` | keep width/`max-w` |
| Header (`:152`) | `border-b border-border-soft px-md py-3.5`; title `text-headline-sm … uppercase` | `border-b border-outline`; eyebrow `.hud text-[10px] text-primary` "Catalog" + count `.hud text-[9px] text-text-dim` | search glyph `search` |
| Match count (`:155`) | `font-mono-sm text-mono-sm text-on-surface-variant` | `font-mono text-[10px] text-text-dim` | "RecAI corpus" / "{n} matches" |
| Close btn (`:158`) | `border-outline-variant bg-surface-container-lowest` | `border border-outline bg-surface-low text-text-variant hover:text-text-main hover:border-primary` | glyph `x` (Sym `close`) |
| Search box (`:170`) | `border-outline-variant bg-surface-container-lowest focus-within:border-primary focus-within:shadow-[0_0_0_3px_var(--primary-tint)]` | `bg-field border border-outline rounded-md focus-within:border-primary`; input `text-[13px] placeholder:text-text-dim text-text-main` | drop the custom tint shadow; border-color shift is enough |
| Result row (`:57`) | `rounded-lg border border-border-soft bg-surface-container-lowest hover:border-primary` | `.panel? no` → `rounded-md border border-outline bg-surface hover:border-primary` | row is a sub-item, no corner accent |
| Row icon tile (`:64`) | `bg-primary/10` + `Sym movie` | `bg-primary/10` + lucide `film` (Sym `movie`) | keep cyan tint |
| Row id chip (`:73`) | `bg-surface-container font-mono-sm text-mono-sm text-on-surface-variant` | `bg-surface-low font-mono text-[10px] text-text-dim` | |
| Expanded body (`:78`) | `border-t border-border-soft`; desc `text-body-sm text-on-surface-variant`; empty `italic text-outline` | `border-t border-outline`; `text-[12px] text-text-variant`; empty `italic text-text-dim` | |
| "Copy id" (`:85`) | `text-primary hover:underline` | unchanged (cyan) | glyph `copy` (Sym `content_copy`) |
| Skeleton (`:222`) | `border-border-soft`; fills `bg-surface-container-high`/`-container` `animate-rb-pulse` | `border-outline`; fills `bg-surface-high`/`bg-surface-low` `animate-pulse` | 6 rows kept |
| Empty (`:198`) | centered `text-body-sm text-on-surface-variant` | adopt the **standard empty anatomy** (§5): lucide `search` tile + line | copy rewrite below |
| Error (`:238`) | `border-error/40 bg-error-container/40`; `Sym error`; retry `border-outline-variant` | `border-danger/30 bg-danger/10`; lucide `alert-triangle`; retry `border border-outline hover:border-primary` | copy rewrite below |

---

## 2. Persona catalog rail · `PersonaCatalog.tsx`

The cockpit's left navigator: header (title + count + search + source-filter chips), then a scrollable
list of `PersonaCard` rows. Keep the debounced query (`:50`), the client-side `source` filter (`:67`),
the dynamic chip set built from real `p.source` values (`:61`), and the loading/empty/error switch
(`:110`). Reskin to the matrAIx rail; the full-screen "Browse personas" grid in the mockup
(`app-redesign-v3.html:433`) is the **same `PersonaCard` dropped into a grid** — see §3 note.

| Element (file:line) | Current | matrAIx target | Notes |
|---|---|---|---|
| Rail (`:75`) | `bg-surface-container-low border-b/-r border-border-soft`; `h-[260px] w-full lg:h-full lg:w-[300px]` | `bg-surface-lowest border-outline`; **keep the responsive sizing** | rail = `surface-lowest` |
| Header block (`:77`) | `border-b border-border-soft p-md pb-sm` | `border-b border-outline` | |
| Title (`:78`) | `text-headline-sm … uppercase tracking-[0.05em] text-on-surface` "Persona Catalog" | eyebrow `.hud text-[10px] text-primary` "Persona catalog" + `font-display text-[15px] font-bold text-text-main` (optional title) | mockup uses eyebrow + display title (`:436`) |
| Count (`:81`) | `text-body-sm text-on-surface-variant` "{n} personas" | `.hud text-[9px] text-text-dim` "{n} loaded" | "…" while loading kept |
| Search (`:89`) | `border-outline-variant bg-surface-container-lowest … focus:border-primary` | `bg-field border border-outline rounded-md focus:border-primary`; glyph `search` `text-text-dim` | placeholder rewrite below |
| Filter chips group (`:99`) | `role="group" aria-label="Filter by source"` | unchanged | keep ARIA |
| `FilterChip` active (`:133`) | `bg-primary text-on-primary` | unchanged (cyan) | keep `aria-pressed` |
| `FilterChip` inactive | `bg-surface-container text-on-surface-variant hover:bg-surface-container-high` | `border border-outline bg-surface text-text-variant hover:border-primary hover:text-text-main` | mockup `.seg` look (`:441`) |
| List (`:109`) | `custom-scrollbar … p-sm` | unchanged (`custom-scrollbar` is a matrAIx utility) | |
| Skeleton (`:145`) | fills `bg-surface-container-high`/`-container` `animate-rb-pulse` | `bg-surface-high`/`bg-surface-low` `animate-pulse` | 7 rows kept |
| Empty (`:166`) | `Sym search_off text-outline` + line | standard empty anatomy: lucide `search-x` (Sym `search_off`) `text-text-dim` + line | copy below |
| Error (`:178`) | `Sym error text-error` + retry `border-outline-variant hover:text-primary` | lucide `alert-triangle text-danger` + retry `border border-outline hover:border-primary` | copy below |

---

## 3. Persona card · `PersonaCard.tsx`

The biggest visual change. Today the card leads with **source** as the heading and a descriptive
title underneath (`:30-34`). The mockup leads with the **occupation / role** as the heading, demotes
source to a tinted provenance chip, and uses a `age · sex · id` micro-label
(`app-redesign-v3.html:1297`). **Re-arrange using the helpers already in `cockpitShared.tsx` — no new
data.**

Field re-mapping (all from existing parsers):
- **Heading** = `personaDescriptiveTitle(null, persona.blurb, persona.source)` (already imported, `:32`) — yields the occupation/role ("Financial Manager") and falls back to "{source} persona" honestly when no role text exists.
- **Source chip** = `persona.source`, tinted per the source-tone map below.
- **Meta micro-label** = age + sex from `parseDemographicsFromBlurb(persona.blurb)` (`:33`) joined as `Age · Sex`, then `· {codename}` from `personaCodename` (`:30`). Render only the parts that parse; if neither age nor sex is present, show just the id.
- **Trait/description line** = the remaining short blurb framing (the current "title" text), clamped to one line.

Source-tone map (port of the mockup's `srcColor`, `app-redesign-v3.html:1294`) — express as a small
constant beside the card; unknown sources fall to the neutral default (never invent a tone):

| `source` | Chip tone |
|---|---|
| `Nemotron` | mint — `text-secondary border-secondary/30 bg-secondary/10` |
| `OASIS` | cyan — `text-primary border-primary/30 bg-primary/10` |
| `PersonaHub` | amber — `text-warn border-warn/30 bg-warn/10` |
| `Curated` / any other | neutral — `text-text-variant border border-outline bg-surface-high` |

| Element (file:line) | Current | matrAIx target | Notes |
|---|---|---|---|
| Card button (`:41`) | `rounded-lg p-sm`; selected `border-primary bg-surface-container-lowest shadow-soft`; idle `border-transparent hover:border-outline-variant hover:bg-surface-variant` | `group relative .panel rounded-md p-4 border`; selected `border-primary bg-surface` (+ `.panel` cyan bracket shows); idle `border-outline bg-surface hover:border-primary` | mockup card = `.panel bg-surface border border-outline hover:border-primary` (`:1297`); drop `shadow-soft` |
| Selected left bar (`:47`) | `w-1 bg-primary` | keep (redundant-with-`.panel` is fine; also a non-color cue) | a11y: not color-only |
| Avatar (`:49`) | `rounded-full`; selected `bg-primary/10` else `bg-surface-container-highest`; `Sym person` | `rounded` (mockup uses square-ish), `bg-surface-high border border-outline group-hover:text-primary`; selected `bg-primary/10 text-primary`; lucide `scan-face` (Sym `person`) | square tile per mockup |
| Heading (`:59`) | `truncate text-body-md font-semibold`; source text; selected `text-primary` | `font-display font-semibold text-[14px] text-text-main` = **role/occupation** | swap content to descriptive title |
| Id chip (`:64`) | `font-mono-sm text-mono-sm`; selected `bg-surface-container` | move into meta line as `font-mono text-text-dim`; **add source chip** top-right tinted per map | source chip replaces the bare id in the header row |
| Title line (`:72`) | `truncate text-body-sm text-on-surface-variant` | becomes **meta** `.hud text-[8px] text-text-dim` = `{Age} · {Sex} · {id}` | render-if-present |
| Trait line (new) | (the old title text) | `text-text-variant text-[11px] leading-snug` one-line description | honest framing only |
| Demographic chips (`:73`) | up to 3 chips `bg-surface-container text-[10px]` | fold age/sex into the meta label; keep an optional occupation chip `bg-surface-low border border-outline text-[11px]` only if not already the heading | avoid duplicating the heading |

> Grid-readiness: the rail keeps its 1-column list. The identical reskinned `PersonaCard` is exactly
> the mockup's grid cell, so a future "Browse personas" full-screen view only needs the grid wrapper
> `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4` (`app-redesign-v3.html:449`).
> Out of scope for the reskin, but the card must not hard-code rail-only assumptions.

---

## 4. Persona detail drawer · `PersonaDrawer.tsx`

Today the drawer is honest-but-bare: identity header + the **verbatim** `context` text in a `<pre>`
(`:99`), with a loading skeleton (`:88`) and a working focus trap + Escape + focus restore
(`:35-47`). The mockup gives it sectioned panels — Demographics / Traits / Goal context / Raw record —
and a "Use this persona" footer (`app-redesign-v3.html:907-1010`).

**Honesty constraint (do not skip):** the personas API returns only `{id, name, source, blurb}` plus a
humanized `context` *text block* — there are **no** structured demographic/trait/JSON fields
(`cockpitShared.tsx:5-10`, `types.ts:296-313`). So:
- **Demographics** = `parseDemographics(fullContext)` (`cockpitShared.tsx:141`) → render only the
  rows that genuinely parse (age / gender / occupation / location). Do **not** add Region/Segment as
  the mockup hints — those are not in the data.
- **Goal context** = the parsed prose sections via `parsePersonaSections(fullContext)`
  (`cockpitShared.tsx:272`) — show the relevant section bodies (e.g. Persona / Background). Reuses
  the same parser the Persona inspector tab uses; still no new data.
- **Traits** = render-if-present only. Curated personas generally have no discrete trait list, so the
  Traits panel is **omitted** when empty rather than shown with placeholder chips.
- **Raw record** = the verbatim `fullContext` (today's `<pre>`), styled as the mockup's "Raw record"
  panel with a Copy button. It is **text**, not JSON — keep it literal.

The drawer keeps its current behaviour and `usePersonaDetail` fetch (`:33`); these are presentational
panels over already-fetched text. Mark the Demographics/Goal panels as the only structural additions.

| Element (file:line) | Current | matrAIx target | Notes |
|---|---|---|---|
| Overlay (`:59`) | `flex items-center justify-center p-6` | mockup uses a right slide-over: `absolute right-0 top-0 bottom-0` is allowed, but the **centered modal is fine to keep** — just reskin | keep whichever; do not change focus logic |
| Scrim (`:60`) | `bg-on-surface/30` | `bg-black/50 backdrop-blur-sm` | |
| Dialog (`:61`) | `rounded-xl border-border-soft bg-surface-container-lowest shadow-pop` | `rounded-md border border-outline bg-surface-lowest shadow-2xl` | keep `role="dialog" aria-modal max-h-[80vh]` |
| Header (`:67`) | `border-b border-border-soft px-4 py-3`; title `text-headline-md font-headline-md`; source `bg-surface-container`; id `font-mono-sm` | `border-b border-outline`; eyebrow `.hud text-[9px] text-text-dim` "Persona" + title `font-display text-[18px] font-bold`; source chip per source-tone map; id `font-mono text-[10px] text-text-dim`; add `scan-face` avatar tile `bg-surface-high border border-outline` | mirrors mockup header (`:898`) |
| Close (`:77`) | `text-on-surface-variant hover:bg-surface-container` | `border border-outline text-text-variant hover:text-text-main hover:border-primary` | glyph `x` (Sym `close`); keep `closeRef` focus |
| Body wrap (`:87`) | `custom-scrollbar overflow-y-auto p-4` | `p-5 space-y-5` | |
| Demographics panel (new) | — | `.panel bg-surface border border-outline rounded-md p-4`; `.hud text-[10px] text-text-dim` head "Demographics"; `space-y-2.5` rows `label .hud text-[9px]` / `value font-mono text-text-variant` | from `parseDemographics`; omit absent rows |
| Goal-context panel (new) | — | `bg-surface border border-outline rounded-md p-4`; head "Goal context"; `text-[12px] text-text-variant leading-relaxed` | from `parsePersonaSections`; omit if none |
| Raw record panel (was `<pre>`, `:99`) | `whitespace-pre-wrap font-mono-sm text-mono-sm text-on-surface-variant` | wrap in `bg-surface border border-outline rounded-md p-4`, head "Raw record" + Copy btn; `<pre>` in `bg-field border border-outline rounded p-3 font-mono text-[10.5px] text-primary leading-relaxed` | port mockup `:984`; **text, not JSON** |
| Copy button (new) | — | `border border-outline px-2 py-1 hover:border-primary`; lucide `copy`; label flips to "Copied" 1.2s | optional, behaviour-only nicety |
| Loading (`:88`) | bar skeletons `bg-surface-container animate-pulse` | `bg-surface-high animate-pulse`; keep `aria-busy` + `aria-label` | |
| Footer (new) | — | `border-t border-outline p-4`; `.glow w-full bg-primary text-on-primary rounded-md py-3.5 font-semibold` "Use this persona" → selects + closes | the single `.glow` CTA; only if a select callback is wired |

---

## 5. Cross-cutting (a) — the standard state set

Every async/empty surface uses **one anatomy** so the app feels consistent:

```
[ icon tile ]   ← w-12/14 rounded-md, tinted by tone (primary/secondary/danger/warn or surface-high+dashed for idle)
Display heading ← font-display font-semibold text-[15px] text-text-main
Helper line     ← text-[12px] text-text-variant leading-snug, ≤ ~300px
[ action ]      ← optional: secondary button (border border-outline) or the single primary/.glow CTA
```

Five states, where each lives, and the matrAIx treatment (ports of `app-redesign-v3.html` States view,
`:568-718`):

| State | Trigger | Where it appears (file:line) | matrAIx target |
|---|---|---|---|
| **Empty** | no selection / no results | Catalog rail `PersonaCatalog.tsx:166`; ⌘K `CatalogDrawer.tsx:198`; centre "Pick a persona" `Trajectory.tsx:86` & "Ready to run" `:193`; inspector panels before a run (Scorecard/PersonaPanel/PromptPanel — other sections) | idle anatomy; icon tile `bg-surface-high border border-dashed border-outline`, glyph `scan-face`; centre empty offers a **Browse catalog** button → opens catalog |
| **Loading / warming** | query in flight, or cold start (`phase==="building"`) | rail skeleton `PersonaCatalog.tsx:145`; ⌘K skeleton `CatalogDrawer.tsx:222`; drawer skeleton `PersonaDrawer.tsx:88`; centre `Trajectory.tsx:145`; status line `PersonaEvalCockpit.tsx:53`; "warming…" `App.tsx:323` | skeletons `bg-surface-high animate-pulse`; warming row = lucide `loader-2 animate-spin text-primary` + line + `.hud text-[8px]` "Cold start · booting chatbot-api sidecar" |
| **Running** | `phase==="running"` | centre live line `Trajectory.tsx:150`; pipeline `ComponentPipeline` (mounted `PersonaEvalCockpit.tsx:414`); status `liveStatusLine :53` | 3-node mini pipeline **Persona → Chatbot → Scorer** (done=mint check, active=cyan dot `animate-pulse`, waiting=outline); indeterminate cyan bar + "turn N of M"; bottom status bar `bg-surface-lowest border-t border-outline` |
| **Error / timeout** | `phase==="error" \|\| "timeout"`, or start failed with `error` | centre `Trajectory.tsx:158`; ⌘K `CatalogDrawer.tsx:238`; rail `PersonaCatalog.tsx:178` | panel `border border-outline border-l-4 border-l-danger`; tile `bg-danger/10 border-danger/30` lucide `alert-triangle`; **Retry** `border-danger/40 bg-danger/10 text-danger` (preserves config); optional "View details" disclosure showing `TimeoutError · 60s` |
| **Preflight not ready** | `GET /api/preflight` `ready:false` or API offline | chip always in top bar `PreflightChip.tsx` (`TopBar.tsx:105`); **new** blocking banner in centre when not-ready and a run is attempted | panel `border-l-4 border-l-warn`; tile `bg-warn/10 border-warn/30` lucide `plug-zap`; inline `bg-field` command `./run_dev.sh` + Copy; **Recheck** button `border-warn/40 bg-warn/10 text-warn` → `preflight.refetch()` |

`PreflightChip.tsx` reskin (keep the four tones + popover + 20s poll):

| Element (file:line) | Current | matrAIx target |
|---|---|---|
| `TONE_CLASS.ready` (`:26`) | `border-success/40 bg-success-container text-on-success-container` | `border-secondary/40 bg-secondary/10 text-secondary` |
| `TONE_CLASS.setup`/`checking` | `…bg-warning-container text-on-warning-container` | `border-warn/40 bg-warn/10 text-warn` |
| `TONE_CLASS.offline` | `…bg-error-container text-on-error-container` | `border-danger/40 bg-danger/10 text-danger` |
| `DOT_CLASS` (`:32`) | `bg-success`/`bg-warning`/`bg-error` | `bg-secondary`/`bg-warn`/`bg-danger`; checking dot `animate-pulse` |
| Popover (`:113`) | `border-border-soft bg-surface-container-lowest shadow-pop` | `border border-outline bg-surface-lowest shadow-2xl`; head `.hud text-[10px] text-text-dim`; pass glyph `check-circle`/`alert-triangle` (`text-secondary`/`text-warn`) | 

---

## 6. Cross-cutting (b) — responsive / mobile

Desktop (`lg+`) keeps the three-column cockpit (`PersonaEvalCockpit.tsx:378`). Below `lg` the layout
already stacks the rail (`PersonaCatalog.tsx:75`, `h-[260px]`) and inspector (`InspectorTabs.tsx:63`,
`h-[320px]`) vertically. That stack is cramped on phones — replace it with a **single primary column +
bottom tab bar + sheets** (mockup mobile frames `app-redesign-v3.html:1066-1205`). Additive layout
state only (`mobileView`); each tab reuses an existing component as its content. No data change.

| Concern | Current | matrAIx target | Notes |
|---|---|---|---|
| Root (`PersonaEvalCockpit.tsx:378`) | `flex flex-col overflow-y-auto lg:flex-row lg:overflow-hidden` | keep; below `lg` show **one** view at a time driven by `mobileView` | conversation is the default mobile view |
| Catalog rail (`PersonaCatalog.tsx:75`) | always present, `h-[260px]` below `lg` | `lg:` keep as rail; below `lg` hide inline and present **as a bottom sheet** opened from the "Catalog" tab | sheet = `fixed inset-x-0 bottom-0 max-h-[85vh] rounded-t-lg bg-surface-lowest border-t border-outline shadow-2xl` |
| Inspector (`InspectorTabs.tsx:63`) | always present, `h-[320px]` below `lg` | `lg:` keep as right rail; below `lg` present **as a bottom sheet** opened from the "Eval" tab; the tablist (Evaluation/Persona/Prompts) lives inside the sheet | inspector-as-sheet |
| Conversation (`Trajectory`, main `:384`) | shares vertical stack | below `lg` it is the full-height primary view | composer/run bar pinned bottom above the tab bar |
| Run CTA | in `RunHeader` | mobile: pinned bottom run bar `bg-surface-lowest border-t border-outline` with the `.glow` primary button (mockup `:1116`) | one CTA only |
| Bottom tab bar (**new**) | — | `lg:hidden` `nav` `grid grid-cols-4 bg-surface-lowest border-t border-outline`; tabs **Chat · Eval · Runs · Catalog** = `flex-col items-center gap-1 py-2`, active `text-primary` else `text-text-dim`, label `.hud text-[7px]` | glyphs `message-square` · `gauge` · `activity` · `users` (mockup `:1131`) |
| Drawer / ⌘K panel | `w-[460px] max-w-[92vw]` | already `max-w-[92vw]`; on phones treat as full-height sheet `w-full` | keep |
| Persona detail drawer | centered modal | below `sm` go full-width bottom sheet `inset-x-0 bottom-0 rounded-t-lg max-h-[90vh]` | keep focus trap |
| Catalog grid (if used) | n/a | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4` | mockup `:449` |

Bottom tab bar is `role="tablist"`; each tab `aria-selected` + sets `mobileView`. Sheets are
`role="dialog" aria-modal`, dismiss on scrim tap + Escape, and trap focus (reuse the drawer pattern in
`PersonaDrawer.tsx:35-47`). Respect the iOS safe area with `pb-[env(safe-area-inset-bottom)]` on the
tab bar and pinned run bar.

---

## 7. Cross-cutting (c) — accessibility

- **Focus-visible rings.** Keep the single `FOCUS_RING` token applied to every interactive element
  (cards, chips, tabs, drawer controls). Update its offset to a matrAIx surface token
  (`cockpitShared.tsx:30`, see §0) so the 2px cyan ring is visible on both `surface-dim` (page) and
  `surface-lowest` (rails/drawers). The mockup's global `:focus-visible{outline:2px solid
  rgb(var(--primary));outline-offset:2px}` (`app-redesign-v3.html:48`) is the fallback for any
  element the token misses.
- **Contrast — dark and light.** Body text uses `text-text-main` (AAA-ish on both themes); secondary
  uses `text-text-variant`; only de-emphasised meta uses `text-text-dim` — never put `text-text-dim`
  on `bg-field` for content the user must read. Verify the per-source chip tones clear 4.5:1: in
  **light** matrAIx, `secondary` (0 150 103), `primary` (0 118 194), `warn` (176 120 16) and `danger`
  (190 50 70) are the contrast-tuned light values — use those token names, never hard-coded hexes, so
  the theme toggle recolors them. HUD micro-labels (`.hud`, often `text-[8px]`) must stay
  `text-text-dim` or stronger, never a tint at low opacity.
- **Color is never the only signal.** Selected persona card pairs `border-primary` **and** the `.panel`
  bracket **and** `aria-pressed` (`PersonaCard.tsx:40`) — keep all three. Source provenance always
  shows the **source word** in the chip, not color alone. Pipeline node status pairs the dot color
  with a text label ("Done"/"Running"/"Waiting"). Score color (mint/amber/rose) always sits beside a
  numeric value.
- **Reduced motion.** Skeleton pulses, the warming spinner, and the indeterminate run bar must yield to
  `@media (prefers-reduced-motion: reduce)` (global rule, mockup `:56`; already honored via
  `index.css` per `PersonaEvalCockpit.tsx:16`). Confirm the matrAIx `animate-pulse`/`animate-spin` and
  the indeterminate bar keyframes are inside that guard so a reduced-motion user sees static
  placeholders, not frozen mid-animation.
- **Focus management / keyboard.** Preserve every existing affordance: ⌘K opens the palette
  (`App.tsx:250`); Escape closes palette/drawer (`CatalogDrawer.tsx:119`, `PersonaDrawer.tsx:39`);
  the drawer restores focus to its opener (`:45`); the inspector is a real roving-tabindex tablist
  (`InspectorTabs.tsx`). New sheets and the bottom tab bar must adopt the same Escape + focus-trap +
  restore behaviour. Filter chips keep `aria-pressed`; the search inputs keep their `aria-label`.

---

## 8. Copy rewrites

All user-facing strings move from terse/machine to friendly, first-time-user tutorial tone while
staying restrained. HUD micro-labels stay real words.

| Location (file:line) | Current text | Friendly rewrite |
|---|---|---|
| Persona search placeholder (`PersonaCatalog.tsx:93`) | `Search personas…` | `Search by role, age, or trait — e.g. "manager" or "student"` |
| Persona rail title (`:78`) | `Persona Catalog` | eyebrow `Persona catalog` + title `Pick who to simulate` |
| Persona count (`:81`) | `{n} personas` | `{n} personas ready` (loading: `Loading personas…`) |
| Filter chip "All" / "Curated" (`:100`) | `All` / `Curated` | `All sources` / `Curated` (tooltip on Curated: "Hand-picked personas we ship by default") |
| Source chips (Nemotron/OASIS/PersonaHub) | bare name | keep name; tooltip "Source dataset: {name}" so a first-timer knows it's provenance |
| Persona empty, no query (`:171`) | `No personas available.` | `No personas to show yet. Try clearing the source filter.` |
| Persona empty, with query (`:171`) | `No personas match "{q}".` | `Nothing matches "{q}". Try a role like "nurse" or a broader term.` |
| Persona load error (`:182`) | `Couldn't load the persona catalog.` | `We couldn't load the personas. Check the backend is running, then retry.` |
| Persona retry button (`:186`) | `Retry` | `Try again` |
| ⌘K palette title (`CatalogDrawer.tsx:154`) | `Catalog` | eyebrow `Catalog search` (sub: "Look up items the recommender can suggest") |
| ⌘K count idle (`:156`) | `RecAI corpus` | `Type to search the catalog` |
| ⌘K search placeholder (`:176`) | `Search titles, descriptions, genres…` | `Search the catalog — titles, genres, or descriptions` |
| ⌘K empty, no query (`:200`) | `Type to search the catalog, or browse the first results below.` | `Start typing to find an item, or browse the first matches below.` |
| ⌘K empty, with query (`:201`) | `No catalog items match "{q}".` | `No items match "{q}". Try a shorter or different word.` |
| ⌘K no-description (`:82`) | `No description in the catalog.` | `This item has no description on file.` |
| ⌘K "Copy id" (`:91`) | `Copy id → {id}` | `Copy this item's id` (tooltip: "Paste it into a prompt to reference this item") |
| ⌘K error (`:239`) | `Catalog search failed.` | `That search didn't go through. Check the connection and try again.` |
| Drawer dialog label (`PersonaDrawer.tsx:64`) | `{title} full persona` | `Full profile for {title}` |
| Drawer empty context (`:100`) | `No persona context available.` | `This persona has no extra profile text — the summary above is all we have.` |
| Centre empty, no persona (`Trajectory.tsx:93-97`) | `Pick a persona to begin` / `Choose one of the curated personas… against RecBot.` | `Pick a persona to begin` / `Choose someone from the catalog on the left. PersonaEval will role-play them, chat with the app for a few turns, and score how well it understood and met their needs.` |
| Centre ready (`:198-201`) | `Ready to run` / `Press R or use the Run button…` | `Ready when you are` / `Press R or click Run — PersonaEval will start the simulated conversation for this persona.` |
| Run-failed heading/body (`:163-165`) | `This run didn't finish` / `The PersonaEval run stopped unexpectedly. Your configuration is unchanged.` | `This run didn't finish` / `Something interrupted the run — your settings are untouched, so you can try again.` |
| Warming line (`PersonaEvalCockpit.tsx:59`, `Trajectory.tsx:146`) | `Warming the chatbot application — this first turn can take a minute.` | keep (already friendly); add sub `.hud`: `Cold start · the app is booting` |
| Running status (`:61-66`) | `Persona is thinking…` / `Chatbot application is thinking…` / `Scoring the conversation…` | `The persona is deciding what to say…` / `The app is working on its reply…` / `Scoring how well the app did…` |
| Preflight chip "Ready" (`PreflightChip.tsx:81`) | `Ready` | `Ready to run` |
| Preflight chip "API offline" (`:78`) | `API offline` / `Start the API to run turns` | `Backend offline` / `Start the PersonaEval backend to run evals` |
| Preflight chip "Setup needed" (`:86-87`) | `Setup needed` / `{n} items need attention` | `Setup needed` / `{n} item(s) need attention before you can run` |
| Preflight popover head (`:115`) | `Readiness checks` | `Before you can run` |

**New copy this section introduces:**

- **Preflight banner (new, centre, not-ready):** heading `Engine not connected`; body `Start the
  PersonaEval backend, then re-check.`; command `./run_dev.sh` (Copy tooltip "Copy command"); action
  `Recheck`.
- **Error "View details" disclosure (new):** summary `View details`, value e.g. `TimeoutError · 60s` —
  the only place a raw error class is shown, and only on demand.
- **Persona card meta tooltip (new):** on the `Age · Sex · id` line, `title="Age · sex · persona id"`
  so a first-timer can decode the micro-label.
- **Persona drawer sections (new):** panel heads `Demographics`, `Goal context`, `Raw record`. Raw
  record Copy button label flips `Copy → Copied`. If Demographics parses nothing, show
  `No demographics on file for this persona.` (do not hide silently). Footer CTA `Use this persona`.
- **Bottom tab bar labels (new, mobile):** `Chat · Eval · Runs · Catalog` (HUD micro-labels, real
  words).
- **Mobile catalog/inspector sheets (new):** sheet headers reuse the rewritten titles ("Pick who to
  simulate", inspector tab names); add a grabber affordance and an `aria-label` matching the title.
- **First-run hint (new, once, dismissible):** a one-line tip near the persona search —
  `Tip: pick a persona, set your run options up top, then press Run to watch the simulated
  conversation.` Store dismissal in `localStorage`; honor reduced-motion (no slide-in).


---

# 07 — Implementation plan: sequencing, risks, QA

This section turns §01–§06 into an ordered, low-risk rollout. The whole effort is a re-skin, so it can land
incrementally behind a green build — each phase typechecks, builds, and is visually QA'd against the mockup
before the next begins. Per the team's preference, the per-surface phases (2–5) are independent and can be
**parallelized with a dynamic workflow** (one agent per surface) once the foundation (Phase 0) is in.

## Sequencing

**Phase 0 — Foundation (§01). Lands first, alone.**
Replace `src/index.css` tokens + base + utilities, replace `tailwind.config.ts`, swap the font `<link>`s and add
the pre-paint theme boot script in `index.html`, add `npm i lucide-react`, reimplement the icon primitive
(`Sym`→`Icon`) over lucide, and add `src/hooks/useTheme.ts`. This **intentionally breaks the build** wherever an
old token/utility name (`bg-surface-container-*`, `text-on-surface*`, `font-body-*`, `<Sym>`) is still used —
that compile error is the migration checklist. Wire the header theme toggle (§01.3) as part of §02.

**Phase 1 — App shell + Chat (§02).** Header (matrAIx wordmark, nav, preflight chip, theme toggle, ⌘K), slim
footer, and the three-pane Chat workbench (rail · thread · composer · inspector). Clears the most-used surface
and proves the token swap end-to-end.

**Phase 2 — Chatbot cockpit (§03).** The largest surface. Also do the optional **shared-primitive
consolidation** (`toneClass`/`PipelineTone`/`MetricTile` → `cockpitShared.tsx`) here so §04 consumes one
definition. Reskins TaskTypeSwitch, app picker, knobs (RecAI-only Domain), the read-only Harbor environment,
the pipeline, the Trajectory/TurnBubble feed (RecommendedItems + ToolPlanFold), and the Scorecard.

**Phase 3 — Survey + Web cockpits (§04).** Consume the §03 primitives; reskin the instrument preview + survey
results, and the website task card + UX-score tiles + screenshot/action trace. No environment panel.

**Phase 4 — Runs (§05).** Option-aware debrief (chatbot scorecard / survey completion+answers / web UX+trace),
the runs list, Compare, and the tokenized red→amber→mint score scale.

**Phase 5 — Catalog + cross-cutting (§06).** ⌘K palette, persona catalog rail/cards, persona detail drawer;
then the shared state set, responsive/mobile behavior, and the accessibility pass.

**Phase 6 — Copy + QA sweep.** Apply every section's copy-rewrite table and the global helper/empty/error/tooltip
text (§01.4), then the full QA pass below. Copy can also be front-loaded per surface; this phase is the
backstop that nothing terse remains.

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Token-rename churn across ~40 components | The §01.4 old→new map is a mechanical find/replace; the Phase-0 build break is the tripwire that no old name survives. |
| Icon migration (Material Symbols → lucide) | Keep the single `Icon` primitive; migrate names per section via the registry; `fill-current` replaces the old `fill` axis. |
| Tailwind v3 alpha syntax | Tokens **must** be `rgb(var(--x) / <alpha-value>)` (literal placeholder) or `bg-x/10` silently goes solid — called out in §01.3. |
| Light-mode contrast/regressions | Light variant is designed in §01.1; QA explicitly screenshots every surface in light; a11y pass checks contrast (§06.7). |
| Per-option correctness regressions | §03–§05 affirm the per-option truths (env Chatbot-only, RecAI-only Domain, 3/3/4 pipelines, distinct scoring); QA exercises all three application types. |
| Theme flash on load | Pre-paint boot script sets `<html>.light` before React mounts (§01.3). |

## QA / acceptance

- **Build gates (every phase):** `npm run typecheck` and `npm run build` clean.
- **Visual QA:** headless Playwright (works in-session, see memory) — screenshot each surface in **dark and
  light** and diff against the corresponding mockup screen; clean up screenshots from the repo root after.
- **Per-option pass:** in the cockpit, exercise Chatbot (RecAI → OpenBB → Medical, confirming env + Domain
  visibility swap), Survey, and Web; in Runs, view all three debrief shapes.
- **States:** force empty / warming / running / error / preflight and confirm each matches §06.5.
- **Accessibility:** focus-visible rings present, dark+light contrast adequate, `prefers-reduced-motion`
  honored, icons decorative-or-labeled (§06.7).
- **Copy:** no engineer-shorthand string survives; spot-check that first-time helper/tooltip text reads well.

## Out of scope (restated)

Backend, data layer, hooks, API, types, routing, and product behavior are unchanged. This is tokens + classes +
icon primitive + UI-only states + copy.
