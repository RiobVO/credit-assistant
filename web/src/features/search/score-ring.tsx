"use client";

import { Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "@/lib/use-reduced-motion";
import { cn } from "@/lib/utils";

// Phase 2 (DS-PHASE-2): 112×112 score donut с tick marks на 25/50/75/100,
// count-up анимацией 0→target и пульсирующим reco-pill снизу.
// Радиус 46, stroke 8 → circumference = 2πr ≈ 289.027.

type Recommendation = "approve" | "review" | "reject";
type Band = "good" | "warn" | "bad";

const CIRCUMFERENCE = 289.027;

// Цвет ring + reco-pill определяется РЕКОМЕНДАЦИЕЙ, а не display_score.
// Иначе display_score=79 (зелёный band) + recommendation=review (yellow) = визуально
// несоответствие: зелёное кольцо с лейблом «На проверку». Recommendation —
// единый source of truth для verdict-цвета.
function bandOfRecommendation(rec: Recommendation): Band {
  if (rec === "approve") return "good";
  if (rec === "review") return "warn";
  return "bad";
}

function bandTokens(band: Band): { stroke: string; pillBg: string; pillFg: string; pillBorder: string } {
  if (band === "good") {
    return {
      stroke: "var(--state-ok-fg)",
      pillBg: "var(--state-ok-bg)",
      pillFg: "var(--state-ok-fg)",
      pillBorder: "var(--state-ok-border)",
    };
  }
  if (band === "warn") {
    return {
      stroke: "var(--state-warn-fg)",
      pillBg: "var(--state-warn-bg)",
      pillFg: "var(--state-warn-fg)",
      pillBorder: "var(--state-warn-border)",
    };
  }
  return {
    stroke: "var(--state-bad-fg)",
    pillBg: "var(--state-bad-bg)",
    pillFg: "var(--state-bad-fg)",
    pillBorder: "var(--state-bad-border)",
  };
}

export function ScoreRing({
  displayScore,
  recommendation,
  recommendationLabel,
  label,
  denominator,
}: {
  displayScore: number;
  recommendation: Recommendation;
  recommendationLabel: string;
  label: string;
  denominator: string;
}) {
  const band = bandOfRecommendation(recommendation);
  const tone = bandTokens(band);
  const reduced = useReducedMotion();
  const [displayed, setDisplayed] = useState(reduced ? displayScore : 0);
  const ringRef = useRef<SVGCircleElement>(null);

  useEffect(() => {
    if (reduced) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync с props при изменении reduced-motion preference
      setDisplayed(displayScore);
      const ring = ringRef.current;
      if (ring) {
        ring.style.transition = "none";
        ring.style.strokeDashoffset = String(
          CIRCUMFERENCE - (CIRCUMFERENCE * displayScore) / 100,
        );
      }
      return;
    }

    // Reset, then animate.
    const ring = ringRef.current;
    if (ring) {
      ring.style.transition = "none";
      ring.style.strokeDashoffset = String(CIRCUMFERENCE);
      // Force reflow before re-enabling transition.
      void ring.getBoundingClientRect();
      requestAnimationFrame(() => {
        ring.style.transition = "stroke-dashoffset 1.4s cubic-bezier(0.16, 0.84, 0.44, 1)";
        ring.style.strokeDashoffset = String(
          CIRCUMFERENCE - (CIRCUMFERENCE * displayScore) / 100,
        );
      });
    }

    const start = performance.now();
    const dur = 1200;
    let raf = 0;
    const step = (now: number): void => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 4);
      setDisplayed(Math.round(displayScore * eased));
      if (t < 1) raf = requestAnimationFrame(step);
      else setDisplayed(displayScore);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [displayScore, reduced]);

  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-[10.5px] font-semibold tracking-[0.1em] text-[var(--ink-3)] uppercase">
        {label}
      </span>
      <div className="relative size-[112px]">
        <svg width="112" height="112" viewBox="0 0 112 112" className="block -rotate-90">
          <circle
            cx="56"
            cy="56"
            r="46"
            strokeWidth="8"
            fill="none"
            stroke="var(--surface-3)"
          />
          <circle
            ref={ringRef}
            cx="56"
            cy="56"
            r="46"
            strokeWidth="8"
            fill="none"
            stroke={tone.stroke}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE}
            style={{
              filter: `drop-shadow(0 3px 8px ${tone.stroke})`,
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[36px] leading-none font-semibold tracking-[-0.04em] tabular-nums text-[var(--ink-1)]">
            {displayed}
          </span>
          <span className="mt-1 text-[11px] text-[var(--ink-3)]">{denominator}</span>
        </div>
      </div>
      <span
        className={cn(
          "mt-0.5 inline-flex items-center gap-1 rounded-full border px-2.5 py-[3px] text-[11px] font-semibold",
        )}
        style={{
          background: tone.pillBg,
          color: tone.pillFg,
          borderColor: tone.pillBorder,
        }}
      >
        <Check className="size-3" strokeWidth={3} />
        {recommendationLabel}
      </span>
    </div>
  );
}

export type { Recommendation };
