/**
 * NASA-panel space field behind the Home globe.
 * Dark: near-black base with a soft blue wash and pale stars.
 * Light: paper-white base with a faint blue bloom and ink-dot stars.
 */
import { useEffect, useRef } from "react";
import { useIsLightTheme } from "../../hooks/useIsLightTheme";

type Star = { x: number; y: number; size: number; phase: number; speed: number };

interface FieldPalette {
  base: string;
  bloom: [string, string, string, string];
  star: (alpha: number) => string;
  fade: [string, string, string];
}

const DARK_FIELD: FieldPalette = {
  // Neutral black base; the blue accent lives only in the tight bloom
  // right behind the globe so the page reads black, not navy.
  base: "#040405",
  bloom: [
    "rgba(93, 127, 150, 0.14)",
    "rgba(51, 72, 92, 0.06)",
    "rgba(24, 38, 54, 0.02)",
    "rgba(4, 4, 5, 0)",
  ],
  star: (a) => `rgba(185, 195, 203, ${a})`,
  fade: ["rgba(4, 4, 5, 0)", "rgba(4, 4, 5, 0.55)", "rgba(4, 4, 5, 0.92)"],
};

const LIGHT_FIELD: FieldPalette = {
  base: "#f4f6f8",
  bloom: [
    "rgba(31, 99, 155, 0.10)",
    "rgba(31, 99, 155, 0.05)",
    "rgba(31, 99, 155, 0.02)",
    "rgba(244, 246, 248, 0)",
  ],
  star: (a) => `rgba(71, 85, 105, ${a * 0.6})`,
  fade: [
    "rgba(244, 246, 248, 0)",
    "rgba(244, 246, 248, 0.55)",
    "rgba(244, 246, 248, 0.92)",
  ],
};

export function CosmicField({ className = "" }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isLight = useIsLightTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const palette = isLight ? LIGHT_FIELD : DARK_FIELD;

    let raf = 0;
    let w = 0;
    let h = 0;
    let t = 0;
    let stars: Star[] = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, rect.width);
      h = Math.max(1, rect.height);
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(90, Math.max(40, Math.round((w * h) / 22000)));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        size: 0.4 + Math.random() * 1.2,
        phase: Math.random() * Math.PI * 2,
        speed: 0.01 + Math.random() * 0.02,
      }));
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = () => {
      const cx = w * 0.5;
      const cy = h * 0.36;

      ctx.fillStyle = palette.base;
      ctx.fillRect(0, 0, w, h);

      // Soft blue bloom behind globe
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(w, h) * 0.48);
      glow.addColorStop(0, palette.bloom[0]);
      glow.addColorStop(0.35, palette.bloom[1]);
      glow.addColorStop(0.7, palette.bloom[2]);
      glow.addColorStop(1, palette.bloom[3]);
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      for (const star of stars) {
        const pulse = 0.45 + 0.55 * (0.5 + 0.5 * Math.sin(t * star.speed + star.phase));
        const dist = Math.hypot(star.x - cx, star.y - cy) / (Math.min(w, h) * 0.5);
        const alpha = (0.15 + 0.35 * pulse) * Math.min(1, dist * 0.9 + 0.15);
        ctx.beginPath();
        ctx.fillStyle = palette.star(alpha);
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
      }

      // Bottom vignette for copy readability
      const fade = ctx.createLinearGradient(0, h * 0.5, 0, h);
      fade.addColorStop(0, palette.fade[0]);
      fade.addColorStop(0.55, palette.fade[1]);
      fade.addColorStop(1, palette.fade[2]);
      ctx.fillStyle = fade;
      ctx.fillRect(0, h * 0.5, w, h * 0.5);

      t += 1;
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, [isLight]);

  return (
    <canvas
      ref={canvasRef}
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      aria-hidden
    />
  );
}
