"use client";

import { useEffect, useId, useRef, useState } from "react";

import { useReducedMotion } from "@/lib/use-reduced-motion";

// Phase 2 (DS-PHASE-2): SVG sparkline 12 мес с hover-tooltip. На наведении —
// vertical cursor + dot + tooltip с реальным месяцем + значением выручки.
// `points` приходит с backend (`/api/bank/borrowers/search`), `formatTooltip`
// собирает строку «Май 26 · 560 млн сум» из ISO-месяца + Decimal-строки.

export type SparklinePoint = {
  /** ISO `YYYY-MM` */
  month: string;
  /** Decimal as string, UZS sum */
  revenue: string;
};

export type SparklineProps = {
  points: SparklinePoint[];
  formatTooltip: (point: SparklinePoint) => string;
  height?: number;
};

const W = 600;
const PAD = 4;

function buildPath(values: number[], h: number): { line: string; area: string } {
  if (values.length === 0) return { line: "", area: "" };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = values.length;
  const sx = (i: number) => PAD + (i * (W - PAD * 2)) / Math.max(1, n - 1);
  const sy = (v: number) => h - PAD - ((v - min) / range) * (h - PAD * 2);
  let d = `M ${sx(0)} ${sy(values[0])}`;
  for (let i = 1; i < n; i++) {
    const px = (sx(i - 1) + sx(i)) / 2;
    const mid = (sy(values[i - 1]) + sy(values[i])) / 2;
    d += ` Q ${sx(i - 1)} ${sy(values[i - 1])} ${px} ${mid}`;
    d += ` T ${sx(i)} ${sy(values[i])}`;
  }
  const area = `${d} L ${sx(n - 1)} ${h} L ${sx(0)} ${h} Z`;
  return { line: d, area };
}

export function RevenueSparkline({
  points,
  formatTooltip,
  height = 48,
}: SparklineProps) {
  const reduced = useReducedMotion();
  const wrapRef = useRef<HTMLDivElement>(null);
  const lineRef = useRef<SVGPathElement>(null);
  const [hover, setHover] = useState<{ idx: number; left: number } | null>(null);
  const gradId = useId();

  const values = points.map((p) => Number(p.revenue));
  const paths = buildPath(values, height);

  // Draw-on-mount animation (1.6s) — stroke-dashoffset на line.
  useEffect(() => {
    if (reduced) return;
    const line = lineRef.current;
    if (!line) return;
    const len = line.getTotalLength();
    line.style.transition = "none";
    line.style.strokeDasharray = String(len);
    line.style.strokeDashoffset = String(len);
    void line.getBoundingClientRect();
    requestAnimationFrame(() => {
      line.style.transition = "stroke-dashoffset 1.6s cubic-bezier(0.4, 0, 0.2, 1)";
      line.style.strokeDashoffset = "0";
    });
  }, [reduced, paths.line]);

  if (points.length === 0) return null;

  const onMove = (e: React.MouseEvent<HTMLDivElement>): void => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, x / rect.width));
    const idx = Math.round(ratio * (points.length - 1));
    const snapX = (idx / Math.max(1, points.length - 1)) * rect.width;
    setHover({ idx, left: snapX });
  };

  const tooltip = hover ? formatTooltip(points[hover.idx]) : null;

  return (
    <div
      ref={wrapRef}
      className="relative w-full"
      onMouseMove={onMove}
      onMouseLeave={() => setHover(null)}
    >
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${W} ${height}`}
        preserveAspectRatio="none"
        className="block"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand-primary)" stopOpacity="0.28" />
            <stop offset="100%" stopColor="var(--brand-primary)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={paths.area} fill={`url(#${gradId})`} opacity={0.55} />
        <path
          ref={lineRef}
          d={paths.line}
          fill="none"
          stroke="var(--brand-primary)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {hover ? (
        <>
          <div
            aria-hidden
            className="pointer-events-none absolute top-0 bottom-0 w-px bg-[var(--ink-2)]"
            style={{ left: hover.left }}
          >
            <div
              className="absolute top-1/2 left-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full border-[1.5px] border-white"
              style={{
                background: "var(--brand-primary)",
                boxShadow:
                  "0 0 0 1px var(--brand-primary), 0 4px 8px -2px color-mix(in oklab, var(--brand-primary) 40%, transparent)",
              }}
            />
          </div>
          <div
            role="tooltip"
            className="pointer-events-none absolute bottom-full left-0 mb-2 -translate-x-1/2 rounded-md bg-[var(--ink-1)] px-2.5 py-1.5 font-mono text-[11px] whitespace-nowrap text-white tabular-nums"
            style={{ left: hover.left }}
          >
            {tooltip}
            <span
              className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent"
              style={{ borderTopColor: "var(--ink-1)" }}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
