"use client";

import { useTranslations } from "next-intl";

import type { SearchCardMonthlyPoint } from "@/lib/bank-api";

// Phase 2 (DS-PHASE-2): chip-bar «Недавние ИНН». Sparkline отображается ТОЛЬКО
// на активном chip (тот, чей ИНН совпадает с current input value). Данные
// sparkline'а — из текущего result.card.monthly_revenue_12m (т.е. mini-эхо
// большой sparkline в ResultCard). Inactive chips — просто моноширинный ИНН.

function formatInn(inn: string): string {
  if (inn.length === 9) {
    return inn.replace(/(\d{3})(\d{3})(\d{3})/, "$1 $2 $3");
  }
  return inn;
}

function buildMiniPath(values: number[], w: number, h: number): string {
  if (values.length === 0) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const n = values.length;
  const sx = (i: number) => (i * w) / Math.max(1, n - 1);
  const sy = (v: number) => h - ((v - min) / range) * h;
  let d = `M ${sx(0).toFixed(1)} ${sy(values[0]).toFixed(1)}`;
  for (let i = 1; i < n; i++) {
    d += ` L ${sx(i).toFixed(1)} ${sy(values[i]).toFixed(1)}`;
  }
  return d;
}

function strokeForTrend(values: number[]): string {
  if (values.length < 2) return "var(--state-neutral-fg)";
  const first = values[0];
  const last = values[values.length - 1];
  if (last > first * 1.05) return "var(--state-ok-fg)";
  if (last < first * 0.95) return "var(--state-bad-fg)";
  return "var(--state-warn-fg)";
}

export type RecentChipsProps = {
  recent: string[];
  activeInn: string;
  activePoints: SearchCardMonthlyPoint[] | null;
  onChipClick: (inn: string) => void;
};

export function RecentChips({
  recent,
  activeInn,
  activePoints,
  onChipClick,
}: RecentChipsProps) {
  const t = useTranslations("bank.search");
  if (recent.length === 0) return null;

  const sparkValues = activePoints?.map((p) => Number(p.revenue)) ?? [];
  const sparkPath = buildMiniPath(sparkValues, 32, 10);
  const sparkStroke = strokeForTrend(sparkValues);

  return (
    <div className="mb-8 flex flex-wrap items-center gap-[10px]">
      <span className="mr-1 text-[12px] text-[var(--ink-3)]">{t("recent")}</span>
      {recent.map((r) => {
        const isActive = r === activeInn;
        return (
          <button
            key={r}
            type="button"
            onClick={() => onChipClick(r)}
            className={`group inline-flex h-[30px] items-center gap-[7px] rounded-full border px-3 font-mono text-[11.5px] transition-all duration-160 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${
              isActive
                ? "border-[var(--ink-2)] text-[var(--ink-1)] shadow-[0_4px_12px_-8px_rgba(14,21,37,0.25)]"
                : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink-2)] hover:-translate-y-px hover:border-[var(--ink-2)] hover:text-[var(--ink-1)] hover:shadow-[0_6px_14px_-8px_rgba(14,21,37,0.25)]"
            }`}
          >
            {formatInn(r)}
            {/* Sparkline отображается ТОЛЬКО на active chip И только при наличии данных. */}
            {isActive && sparkValues.length >= 2 ? (
              <svg
                width="32"
                height="10"
                viewBox="0 0 32 10"
                fill="none"
                stroke={sparkStroke}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="shrink-0"
                aria-hidden
              >
                <path d={sparkPath} />
              </svg>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
