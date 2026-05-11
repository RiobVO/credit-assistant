"use client";

import { TrendingDown, TrendingUp } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

import { cn } from "@/lib/utils";

import { formatYoy } from "./format";

type ChangeTone = "positive" | "negative";
type LevelTone = "good" | "warn" | "bad";

// CA-048: 4px left severity stripe — ортогональный сигнал absolute-level порога.
// Не конфликтует с YoY pill (один visual канал = один сигнал). Цвета берутся
// из дизайн-токенов (см. globals.css), палитра в одном месте.
const LEVEL_STRIPE_CLASS: Record<LevelTone, string> = {
  good: "border-l-4 border-l-[var(--ca-success)]",
  warn: "border-l-4 border-l-[var(--ca-warning)]",
  bad: "border-l-4 border-l-[var(--ca-danger)]",
};

export function KpiCard({
  label,
  value,
  yoyPct,
  changeTone,
  sparkline,
  tooltip,
  levelTone,
}: {
  label: string;
  value: string;
  yoyPct: number | null; // null когда нет предыдущего периода для сравнения
  changeTone: ChangeTone;
  sparkline: number[];
  // CA-037: опциональный подсказывающий title на карточке (для EBIT-прокси
  // объясняет, что D&A недоступен и величина — EBIT, не EBITDA).
  tooltip?: string;
  // CA-048: absolute-level threshold tone (good/warn/bad). undefined → нет
  // stripe (для KPI без universal threshold — revenue_ltm, ebit).
  levelTone?: LevelTone;
}) {
  const data = sparkline.map((y, i) => ({ i, y }));

  const tone =
    changeTone === "positive"
      ? "border-[#BFE2D2] bg-[var(--ca-success-50)] text-[var(--ca-success)]"
      : "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--ca-danger)]";

  const sparkColor = changeTone === "positive" ? "#0F8A5F" : "#B42318";
  const Icon = changeTone === "positive" ? TrendingUp : TrendingDown;

  return (
    <div
      className={cn(
        "rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]",
        levelTone && LEVEL_STRIPE_CLASS[levelTone],
      )}
      title={tooltip}
    >
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-ink-400)] uppercase">
        {label}
      </div>

      <div className="mt-2 flex items-end justify-between gap-2">
        <span className="font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ca-ink-900)]">
          {value}
        </span>
        {yoyPct !== null && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-px text-[11px] font-semibold",
              tone,
            )}
          >
            <Icon className="size-3" />
            {formatYoy(yoyPct)}
          </span>
        )}
      </div>

      <div className="mt-3 h-[36px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
            <defs>
              <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={sparkColor} stopOpacity={0.35} />
                <stop offset="100%" stopColor={sparkColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="y"
              stroke={sparkColor}
              strokeWidth={1.6}
              fill={`url(#spark-${label})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
