// CA-035: Чек-лист «Перед отправкой на скоринг» поверх Data Readiness Service.
//
// Watches step1.inn + step2 (revenue/netProfit/balance), деribounce 500ms,
// POST /api/manual-input/readiness, рендерит:
// - ИНН ГНК (existing tri-state на client side)
// - Pill верхнего уровня по DataReadinessLevel (red/amber/green)
// - Список missing_capabilities как amber-сноски
// - confidence_score процентом
//
// Tri-state ChecklistRow (ok/warn/pending) расширяет existing 2-state
// (boolean done). Палитра pending — red, как RiskChip danger в CA-033.

"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Check, Info, TriangleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { useFormContext, useWatch } from "react-hook-form";

import { assessReadiness, type DataReadinessRequest } from "@/lib/api";
import { cn } from "@/lib/utils";

import { digitsOnly, hasAnyQuarterValue, yearTotal } from "../lib/finance";
import { useSourceTrail } from "../hooks/use-source-trail";
import type { FormValues } from "../schema";

type Status = "ok" | "warn" | "pending";

const KNOWN_YEARS = [2023, 2024, 2025] as const;

const CAPABILITY_KEY: Record<
  string,
  | "checklist_cap_yoy_trend"
  | "checklist_cap_cagr"
  | "checklist_cap_balance_ratios"
  | "checklist_cap_tax_burden"
> = {
  yoy_trend: "checklist_cap_yoy_trend",
  cagr: "checklist_cap_cagr",
  balance_ratios: "checklist_cap_balance_ratios",
  tax_burden: "checklist_cap_tax_burden",
};

const LEVEL_KEY: Record<
  string,
  | "checklist_level_insufficient"
  | "checklist_level_minimal"
  | "checklist_level_standard"
  | "checklist_level_comprehensive"
> = {
  insufficient: "checklist_level_insufficient",
  minimal: "checklist_level_minimal",
  standard: "checklist_level_standard",
  comprehensive: "checklist_level_comprehensive",
};

const LEVEL_STATUS: Record<string, Status> = {
  insufficient: "pending",
  minimal: "warn",
  standard: "warn",
  comprehensive: "ok",
};

export function Checklist() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const inn = useWatch({ control, name: "step1.inn" });
  const innValid = /^\d{9}$/.test(inn ?? "");

  const revenue = useWatch({ control, name: "step2.revenue" });
  const profit = useWatch({ control, name: "step2.netProfit" });
  const { sourceTrail } = useSourceTrail();

  // Аналитический срез form state — то что бэкенд ожидает в body.
  // Считаем синхронно из watches; useQuery дебаунсит сетевой запрос.
  const liveRequest = useMemo<DataReadinessRequest>(
    () => buildRequest(revenue, profit, sourceTrail),
    [revenue, profit, sourceTrail],
  );

  // Debounce: 500ms тишины после последнего изменения form → новый запрос.
  // Без него каждый keystroke триггерит POST.
  const debounced = useDebouncedValue(liveRequest, 500);

  const readiness = useQuery({
    queryKey: ["readiness", debounced],
    queryFn: () => assessReadiness(debounced),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });

  const readinessLine = readiness.isLoading
    ? t("checklist_assessing")
    : readiness.isError
      ? t("checklist_assess_error")
      : readiness.data
        ? t("checklist_ready_template", {
            level: t(LEVEL_KEY[readiness.data.level]),
            confidence: formatConfidence(readiness.data.confidence_score),
          })
        : t("checklist_awaiting");

  return (
    <>
      <h3 className="my-3.5 text-[14px] font-semibold text-[var(--ink-1)]">
        {t("checklist_heading")}
      </h3>
      <div className="flex flex-col gap-2.5">
        <ChecklistRow status={innValid ? "ok" : "warn"}>
          {t("checklist_inn_confirmed")}
        </ChecklistRow>

        <ChecklistRow status={readiness.data ? LEVEL_STATUS[readiness.data.level] : "warn"}>
          {readinessLine}
        </ChecklistRow>

        {readiness.data?.missing_capabilities.map((cap) => (
          <CapabilityRow
            key={cap}
            label={CAPABILITY_KEY[cap] ? t(CAPABILITY_KEY[cap]) : cap}
          />
        ))}

        <ChecklistRow status="warn">
          {t("checklist_optional_contract")}
        </ChecklistRow>
      </div>
    </>
  );
}

// Tri-state row (ok = green check / warn = amber «!» / pending = red «✕»).
function ChecklistRow({
  status,
  children,
}: {
  status: Status;
  children: React.ReactNode;
}) {
  const palette = {
    ok: "border-[#BFE2D2] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
    warn: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--state-warn-fg)]",
    pending: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--state-bad-fg)]",
  }[status];
  const Icon =
    status === "ok" ? Check : status === "pending" ? X : TriangleAlertSmall;

  return (
    <div className="flex items-center gap-2.5 text-[13px] text-[var(--ink-2)]">
      <span
        className={cn(
          "grid size-[18px] flex-none place-items-center rounded border",
          palette,
        )}
      >
        <Icon />
      </span>
      {children}
    </div>
  );
}

// Inline sub-row для missing_capabilities (без иконки слева, с offset).
function CapabilityRow({ label }: { label: string }) {
  return (
    <div className="ml-7 flex items-center gap-2 text-[12px] text-[var(--ink-3)]">
      <Info className="size-3.5 text-[var(--state-warn-fg)]" />
      {label}
    </div>
  );
}

function TriangleAlertSmall() {
  return <TriangleAlert className="size-2.5" />;
}

// === helpers ===

function buildRequest(
  revenue: FormValues["step2"]["revenue"] | undefined,
  profit: FormValues["step2"]["netProfit"] | undefined,
  sourceTrail: Record<string, string>,
): DataReadinessRequest {
  const annualYears = new Set<number>();
  const fullQuarterYears = new Set<number>();
  const partialQuarterYears = new Set<number>();

  for (const y of KNOWN_YEARS) {
    const yKey = `y${y}` as const;
    const yearRevenue = revenue?.[yKey];
    const yearProfit = profit?.[yKey];

    // Согласовано с CA-027 yearTotal-семантикой: если есть annual revenue
    // (через annual cell ИЛИ sum заполненных квартальных cells) → считаем
    // что у нас есть «годовой total» за этот год, эквивалент annual report.
    // Это держит readiness в согласии с pre-score gauge (тот тоже uses
    // sumQuarters как proxy для annual revenue).
    const revenueAnnualTotal = yearRevenue ? yearTotal(yearRevenue) : 0;
    const allQuartersFilled =
      yearRevenue !== undefined &&
      (["q1", "q2", "q3", "q4"] as const).every(
        (q) => digitsOnly(yearRevenue[q] ?? "").length > 0,
      );
    const hasPartialProfit =
      yearProfit !== undefined && hasAnyQuarterValue(yearProfit);

    if (allQuartersFilled) {
      // 4 quarters revenue заполнены → full coverage (квартальная гранулярность).
      fullQuarterYears.add(y);
    } else if (revenueAnnualTotal > 0) {
      // Есть годовая выручка (хотя бы один квартал ИЛИ annual cell) — proxy
      // для annual report. Domain поднимет уровень до MINIMAL.
      annualYears.add(y);
    } else if (hasPartialProfit) {
      // Только profit без revenue (странный кейс) — partial.
      partialQuarterYears.add(y);
    }
  }

  return {
    annual_report_years: [...annualYears].sort(),
    full_quarter_years: [...fullQuarterYears].sort(),
    partial_quarter_years: [...partialQuarterYears].sort(),
    source_trail: sourceTrail,
  };
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

function formatConfidence(decimalStr: string): string {
  const n = Number.parseFloat(decimalStr);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}
