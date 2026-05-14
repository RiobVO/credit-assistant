// Полудуга 180° с 4 цветными секторами (red→orange→yellow→green слева направо).
// Стрелка-указатель: вертикальная линия в центре, повёрнутая на (score-50)*1.8°.
// Шкала «выше = лучше» (banking-UX), не совпадает с domain risk_score (0-14 = approve);
// маппер score→display_score выполняется на backend (Phase 3.B).
//
// Phase 9: SectionCard shell без icon-tile (banking-минимализм для read-only).
"use client";

import { useTranslations } from "next-intl";

import { SectionCard } from "@/components/section-card";
import type { Recommendation } from "@/lib/api";
import { cn } from "@/lib/utils";

const SECTORS = [
  { from: 180, to: 135, color: "var(--chart-red)" }, // red — 0–25
  { from: 135, to: 90, color: "var(--chart-orange)" }, // orange — 25–50
  { from: 90, to: 45, color: "var(--chart-yellow)" }, // yellow — 50–75
  { from: 45, to: 0, color: "var(--chart-green)" }, // green — 75–100
] as const;

const RECOMMENDATION_KEY: Record<
  Recommendation,
  "rec_approve" | "rec_review" | "rec_reject"
> = {
  approve: "rec_approve",
  review: "rec_review",
  reject: "rec_reject",
};

const RECOMMENDATION_TONE: Record<Recommendation, string> = {
  approve:
    "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
  review:
    "border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] text-[var(--state-warn-fg)]",
  reject:
    "border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]",
};

export function ScoreGauge({
  score,
  recommendation,
}: {
  score: number;
  recommendation: Recommendation;
}) {
  const t = useTranslations("dossier.score");
  const clamped = Math.max(0, Math.min(100, score));
  const needleRotation = (clamped - 50) * 1.8;

  return (
    <SectionCard title={t("section_title")} sub={t("section_sub")}>
      <div className="flex flex-col items-center pt-2 pb-1">
        <svg
          viewBox="0 0 220 130"
          className="w-full max-w-[280px]"
          aria-hidden="true"
        >
          {SECTORS.map((s, i) => (
            <path
              key={i}
              d={arcPath(110, 115, 90, s.from, s.to)}
              stroke={s.color}
              strokeWidth={16}
              strokeLinecap="butt"
              fill="none"
            />
          ))}
          <line
            x1={110}
            y1={115}
            x2={110}
            y2={37}
            stroke="var(--ink-1)"
            strokeWidth={3}
            strokeLinecap="round"
            transform={`rotate(${needleRotation} 110 115)`}
          />
          <circle cx={110} cy={115} r={6} fill="var(--ink-1)" />
        </svg>

        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="font-mono text-[56px] leading-none font-bold tracking-[-2px] text-[var(--ink-1)]">
            {clamped}
          </span>
          <span className="font-mono text-[18px] font-semibold text-[var(--ink-4)]">
            / 100
          </span>
        </div>

        <span
          className={cn(
            "mt-3 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-semibold",
            RECOMMENDATION_TONE[recommendation],
          )}
        >
          <span className="size-1.5 rounded-full bg-current opacity-70" />
          {t(RECOMMENDATION_KEY[recommendation])}
        </span>
      </div>
    </SectionCard>
  );
}

function arcPath(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number,
): string {
  const [x1, y1] = polar(cx, cy, r, startDeg);
  const [x2, y2] = polar(cx, cy, r, endDeg);
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  // Идём по часовой стрелке (decreasing angle) → sweep=1.
  const sweep = startDeg > endDeg ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} ${sweep} ${x2} ${y2}`;
}

function polar(cx: number, cy: number, r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy - r * Math.sin(rad)];
}
