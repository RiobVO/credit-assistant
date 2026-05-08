"use client";

import { TrendingDown, TrendingUp } from "lucide-react";

import { cn } from "@/lib/utils";

import { formatYoy } from "./format";

type ChangeTone = "positive" | "negative";
type LevelTone = "good" | "warn" | "bad";

// CA-048: 4px left severity stripe — ортогональный сигнал absolute-level порога.
// Не конфликтует с YoY pill (один visual канал = один сигнал). Цвета берутся
// из дизайн-токенов (см. globals.css), палитра в одном месте.
const LEVEL_STRIPE_CLASS: Record<LevelTone, string> = {
  good: "border-l-4 border-l-[var(--state-ok-fg)]",
  warn: "border-l-4 border-l-[var(--state-warn-fg)]",
  bad: "border-l-4 border-l-[var(--state-bad-fg)]",
};

// Phase 9 design statement: sparkline блок удалён физически. Backend никогда
// не заполнял KpiValueOutput.sparkline для EBIT/ROE/Debt — годовых точек FORM_2
// (3) слишком мало для волны. Когда подключится monthly-проекция EBIT (см.
// TODO[CA-DS25]) — вернётся отдельным компонентом. Сейчас 36+12 px высвобождены
// для плотного KPI row.
export function KpiCard({
  label,
  value,
  yoyPct,
  changeTone,
  tooltip,
  levelTone,
}: {
  label: string;
  value: string;
  yoyPct: number | null; // null когда нет предыдущего периода для сравнения
  changeTone: ChangeTone;
  // CA-037: опциональный подсказывающий title на карточке (для EBIT-прокси
  // объясняет, что D&A недоступен и величина — EBIT, не EBITDA).
  tooltip?: string;
  // CA-048: absolute-level threshold tone (good/warn/bad). undefined → нет
  // stripe (для KPI без universal threshold — revenue_ltm, ebit).
  levelTone?: LevelTone;
}) {
  const tone =
    changeTone === "positive"
      ? "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
      : "border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]";

  const Icon = changeTone === "positive" ? TrendingUp : TrendingDown;

  return (
    <div
      className={cn(
        "rounded-[10px] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]",
        levelTone && LEVEL_STRIPE_CLASS[levelTone],
      )}
      title={tooltip}
    >
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ink-4)] uppercase">
        {label}
      </div>

      <div className="mt-2 flex items-end justify-between gap-2">
        <span className="font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ink-1)]">
          {value}
        </span>
        {yoyPct !== null && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full border px-2 py-px font-mono text-[11px] font-semibold tabular-nums",
              tone,
            )}
          >
            <Icon className="size-3" />
            {formatYoy(yoyPct)}
          </span>
        )}
      </div>
    </div>
  );
}
