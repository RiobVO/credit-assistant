// Полудуга 180° с 4 цветными секторами (red→orange→yellow→green слева направо).
// Стрелка-указатель: вертикальная линия в центре, повёрнутая на (score-50)*1.8°.
// Шкала «выше = лучше» (banking-UX), не совпадает с domain risk_score (0-14 = approve);
// в Phase 3.B будет маппер score→display_score, сейчас mock уже в banking-шкале.

import type { Recommendation } from "@/lib/api";
import { cn } from "@/lib/utils";

const SECTORS = [
  { from: 180, to: 135, color: "#B42318" }, // red — 0–25
  { from: 135, to: 90, color: "#E07A2A" }, // orange — 25–50
  { from: 90, to: 45, color: "#D4A815" }, // yellow — 50–75
  { from: 45, to: 0, color: "#0F8A5F" }, // green — 75–100
] as const;

const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  approve: "Рекомендация: одобрить",
  review: "Рекомендация: на проверку",
  reject: "Рекомендация: отказ",
};

const RECOMMENDATION_TONE: Record<Recommendation, string> = {
  approve: "border-[#BFE2D2] bg-[var(--ca-success-50)] text-[var(--ca-success)]",
  review: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--ca-warning)]",
  reject: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--ca-danger)]",
};

export function ScoreGauge({
  score,
  recommendation,
}: {
  score: number;
  recommendation: Recommendation;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const needleRotation = (clamped - 50) * 1.8;

  return (
    <div className="rounded-[10px] border border-[var(--ca-border)] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <div className="flex flex-col items-center px-6 pt-6 pb-5">
        <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-ink-400)] uppercase">
          Скоринговый балл
        </div>

        <svg
          viewBox="0 0 220 130"
          className="mt-2 w-full max-w-[280px]"
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
            stroke="#0E1525"
            strokeWidth={3}
            strokeLinecap="round"
            transform={`rotate(${needleRotation} 110 115)`}
          />
          <circle cx={110} cy={115} r={6} fill="#0E1525" />
        </svg>

        <div className="mt-3 flex items-baseline gap-1.5">
          <span className="font-mono text-[56px] leading-none font-bold tracking-[-2px] text-[var(--ca-ink-900)]">
            {clamped}
          </span>
          <span className="font-mono text-[18px] font-semibold text-[var(--ca-ink-400)]">
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
          {RECOMMENDATION_LABEL[recommendation]}
        </span>
      </div>
    </div>
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
