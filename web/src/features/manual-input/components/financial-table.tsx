"use client";

// Phase 7: annual-default режим. По умолчанию — 3 годовых cell (по одной на
// 2023/2024/2025), значение пишется в quarter.annual (CA-027 fallback). Toggle
// «Показать кварталы» раскрывает 4×3 grid с квартальными inputs.
//
// Backend контракт (CA-027 yearTotal): если quarterly заполнены — sum побеждает
// annual; если quarterly пустые — берётся annual. UI отражает это: при раскрытых
// кварталах годовая cell становится disabled с проставленным sum-of-quarters
// (read-only); при закрытых — наоборот, годовая editable, кварталы спрятаны.

import { ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { cn } from "@/lib/utils";

import {
  computeCagrPct,
  computeMarginPct,
  digitsOnly,
  formatUzs,
  hasAnyQuarterValue,
  sumQuarters,
  yearTotal,
} from "../lib/finance";
import type { FormValues } from "../schema";

import { SourceHint, type SourceState } from "./step-2-financials";
import { useSourceTrail } from "../hooks/use-source-trail";

type SectionPath = "step2.revenue" | "step2.netProfit";
type Variant = "revenue" | "netProfit";

const YEARS = [2023, 2024, 2025] as const;
type Year = (typeof YEARS)[number];
type YearKey = `y${Year}`;

const SOURCE_TRAIL_KEYS: Record<Variant, Record<Year, string>> = {
  revenue: {
    2023: "revenue_2023",
    2024: "revenue_2024",
    2025: "revenue_2025",
  },
  netProfit: {
    2023: "net_profit_2023",
    2024: "net_profit_2024",
    2025: "net_profit_2025",
  },
};

export function FinancialTable({
  basePath,
  variant,
}: {
  basePath: SectionPath;
  variant: Variant;
}) {
  const t = useTranslations("accountant.manual_input");
  const [quartersOpen, setQuartersOpen] = useState(false);

  return (
    <div className="flex flex-col gap-[16px]">
      <div className="flex flex-col gap-[14px]">
        {YEARS.map((year) => (
          <YearlyRow
            key={year}
            basePath={basePath}
            variant={variant}
            year={year}
            quartersOpen={quartersOpen}
          />
        ))}
      </div>

      <TrendFooter basePath={basePath} variant={variant} />

      <div>
        <button
          type="button"
          onClick={() => setQuartersOpen((v) => !v)}
          aria-expanded={quartersOpen}
          className="inline-flex items-center gap-2 rounded-[7px] text-[12.5px] font-medium text-[var(--ink-3)] transition-colors hover:text-[var(--brand-primary)]"
        >
          <ChevronRight
            className={cn(
              "size-[14px] transition-transform duration-200 ease-out",
              quartersOpen && "rotate-90",
            )}
          />
          {quartersOpen
            ? t("s2_quarter_toggle_hide")
            : t("s2_quarter_toggle_show")}
        </button>

        <div
          className={cn(
            "grid transition-[grid-template-rows] duration-220 ease-out",
            quartersOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
          )}
        >
          <div className="overflow-hidden">
            <QuarterGrid basePath={basePath} open={quartersOpen} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────── YearlyRow ────────────────────────────────────────────────────

function YearlyRow({
  basePath,
  variant,
  year,
  quartersOpen,
}: {
  basePath: SectionPath;
  variant: Variant;
  year: Year;
  quartersOpen: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  const yKey = `y${year}` as YearKey;
  const { control } = useFormContext<FormValues>();
  const yearData = useWatch({ control, name: `${basePath}.${yKey}` });
  const { sourceTrail } = useSourceTrail();

  const trailKey = SOURCE_TRAIL_KEYS[variant][year];
  const sourceFromParser = Boolean(sourceTrail[trailKey]);
  const hasQuarterValues =
    yearData !== undefined && hasAnyQuarterValue(yearData);
  const annualOnly = digitsOnly(yearData?.annual ?? "").length > 0;
  const sumQ = yearData ? sumQuarters(yearData) : 0;
  const total = yearData ? yearTotal(yearData) : 0;

  // CA-027: когда юзер раскрыл кварталы и заполнил хоть один — годовая cell
  // становится read-only с вычисленной суммой. Иначе — editable annual input.
  const lockedToQuarters = quartersOpen && hasQuarterValues;

  // Source-state для подсказки.
  const state: SourceState =
    sourceFromParser
      ? "auto"
      : annualOnly || hasQuarterValues
        ? "manual"
        : "waiting";

  return (
    <div className="grid grid-cols-[100px_1fr] items-start gap-[14px]">
      <div className="pt-[12px] text-right">
        <div className="font-mono text-[13px] font-bold tracking-[0.04em] text-[var(--ink-2)]">
          {year}
        </div>
        <div className="mt-[2px] text-[10px] font-medium tracking-normal text-[var(--ink-4)] uppercase">
          {t(yearAgeKey(year))}
        </div>
      </div>

      <div className="flex flex-col gap-[6px]">
        <Controller
          control={control}
          name={`${basePath}.${yKey}.annual` as const}
          render={({ field }) => (
            <div className="relative flex items-stretch">
              <span
                aria-hidden
                className={cn(
                  "pointer-events-none absolute top-0 bottom-0 left-0 z-[1] w-[3px] rounded-l-[10px]",
                  state === "auto" && "bg-[var(--state-ok-fg)]",
                )}
              />
              <input
                ref={field.ref}
                value={
                  lockedToQuarters
                    ? formatUzs(String(sumQ))
                    : formatUzs((field.value as string) ?? "")
                }
                onBlur={field.onBlur}
                onChange={(e) => field.onChange(digitsOnly(e.target.value))}
                readOnly={lockedToQuarters}
                inputMode="numeric"
                placeholder="0"
                className={cn(
                  "h-[42px] flex-1 rounded-l-[10px] border border-r-0 border-[var(--border-strong)] bg-[var(--surface)] px-[14px] text-right font-mono text-[15px] font-medium tabular-nums text-[var(--ink-1)] outline-none transition-colors placeholder:text-[var(--ink-4)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]",
                  lockedToQuarters &&
                    "cursor-not-allowed bg-[var(--surface-2)] text-[var(--ink-2)]",
                )}
              />
              <div
                className={cn(
                  "grid place-items-center rounded-r-[10px] border border-l-0 px-[14px] font-mono text-[11.5px] font-bold tracking-[0.04em]",
                  state === "auto"
                    ? "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
                    : "border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--ink-3)]",
                )}
              >
                UZS
              </div>
            </div>
          )}
        />
        {lockedToQuarters ? (
          <div className="text-[11px] text-[var(--ink-4)]">
            {t("s2_year_locked_to_quarters", {
              total: formatUzs(String(sumQ)),
            })}
          </div>
        ) : (
          <SourceHintForYear
            sourceFromParser={sourceFromParser}
            state={state}
            year={year}
            total={total}
          />
        )}
      </div>
    </div>
  );
}

function SourceHintForYear({
  sourceFromParser,
  state,
  year,
  total,
}: {
  sourceFromParser: boolean;
  state: SourceState;
  year: Year;
  total: number;
}) {
  const t = useTranslations("accountant.manual_input");
  // 2023: FORM_2 одиночный даёт current+prior = 2024+2025, не 2023. Аналитик
  // вводит руками либо загружает второй FORM_2 за предыдущий период.
  if (year === 2023 && !sourceFromParser && total === 0) {
    return (
      <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--ink-4)]">
        <span>{t("s2_revenue_2023_hint")}</span>
      </div>
    );
  }
  // Для остальных годов — стандартный SourceHint (auto / manual / waiting).
  return (
    <SourceHint
      state={state}
      fieldName={`fin_${year}`} // dummy: SourceHint sourceTag берёт из map; для year-row передаём tag вручную
    />
  );
}

function yearAgeKey(year: Year): string {
  const current = new Date().getFullYear();
  if (year === current) return "s2_year_age_current";
  if (year === current - 1) return "s2_year_age_prev";
  return "s2_year_age_older";
}

// ─────────── TrendFooter (CAGR / Margin pill) ───────────────────────────

function TrendFooter({
  basePath,
  variant,
}: {
  basePath: SectionPath;
  variant: Variant;
}) {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const data = useWatch({ control, name: basePath });

  if (!data) return null;

  const total2023 = yearTotal(data.y2023);
  const total2025 = yearTotal(data.y2025);

  // CAGR для revenue: 2023 → 2025 (2 года).
  // Margin для profit: profit_2025 / revenue_2025.
  if (variant === "revenue") {
    const cagr = computeCagrPct(total2023, total2025, 2);
    return (
      <FooterShell
        label={t("table_cagr_label")}
        pill={<RatioPill value={cagr} />}
        sub={t("table_cagr_sub")}
      />
    );
  }

  return <MarginFooter />;
}

function MarginFooter() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const revenue = useWatch({ control, name: "step2.revenue.y2025" });
  const profit = useWatch({ control, name: "step2.netProfit.y2025" });
  const r = revenue ? yearTotal(revenue) : 0;
  const p = profit ? yearTotal(profit) : 0;
  const margin = computeMarginPct(p, r);
  return (
    <FooterShell
      label={t("table_margin_label")}
      pill={<RatioPill value={margin} />}
      sub={t("table_margin_sub")}
    />
  );
}

function FooterShell({
  label,
  pill,
  sub,
}: {
  label: string;
  pill: React.ReactNode;
  sub: string;
}) {
  return (
    <div className="flex items-center gap-[12px] rounded-[11px] border border-dashed border-[var(--border-strong)] bg-[var(--surface-2)] px-[16px] py-[12px]">
      <span className="text-[11.5px] font-bold tracking-[0.08em] text-[var(--ink-3)] uppercase">
        {label}
      </span>
      {pill}
      <span className="text-[11.5px] text-[var(--ink-4)]">— {sub}</span>
    </div>
  );
}

function RatioPill({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className="inline-flex items-baseline gap-[3px] rounded-full border border-[var(--border)] bg-[var(--surface)] px-[10px] py-[3px] font-mono text-[12.5px] font-bold text-[var(--ink-4)]">
        —
      </span>
    );
  }
  const tone =
    value > 0
      ? "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
      : value < 0
        ? "border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]"
        : "border-[var(--border)] bg-[var(--surface)] text-[var(--ink-4)]";
  const sign = value > 0 ? "+" : "";
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-[3px] rounded-full border px-[10px] py-[3px] font-mono text-[12.5px] font-bold tabular-nums",
        tone,
      )}
    >
      {`${sign}${value.toFixed(1).replace(".", ",")}%`}
    </span>
  );
}

// ─────────── QuarterGrid (раскрывается по toggle) ───────────────────────

function QuarterGrid({
  basePath,
  open,
}: {
  basePath: SectionPath;
  open: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="mt-[12px] overflow-hidden rounded-[10px] border border-[var(--border)]">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            <Th first>{t("table_period")}</Th>
            <Th>Q1</Th>
            <Th>Q2</Th>
            <Th>Q3</Th>
            <Th>Q4</Th>
          </tr>
        </thead>
        <tbody>
          {YEARS.map((year) => {
            const yKey = `y${year}` as YearKey;
            return (
              <tr key={year}>
                <FirstCell>{year}</FirstCell>
                <CellInput
                  name={`${basePath}.${yKey}.q1` as const}
                  disabled={!open}
                />
                <CellInput
                  name={`${basePath}.${yKey}.q2` as const}
                  disabled={!open}
                />
                <CellInput
                  name={`${basePath}.${yKey}.q3` as const}
                  disabled={!open}
                />
                <CellInput
                  name={`${basePath}.${yKey}.q4` as const}
                  disabled={!open}
                />
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="border-t border-dashed border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-[11px] leading-[1.5] text-[var(--ink-4)]">
        {t("s2_quarter_note")}
      </div>
    </div>
  );
}

function Th({
  children,
  first,
}: {
  children: React.ReactNode;
  first?: boolean;
}) {
  return (
    <th
      className={cn(
        "border-b border-[var(--border)] bg-[var(--surface)] px-3 py-[10px] text-[10.5px] font-bold tracking-[0.08em] text-[var(--ink-4)] uppercase shadow-[inset_0_-1px_0_var(--border)]",
        first
          ? "rounded-tl-[10px] border-l-0 text-left"
          : "border-l border-[var(--border)] text-right",
      )}
    >
      {children}
    </th>
  );
}

function FirstCell({ children }: { children: React.ReactNode }) {
  return (
    <td className="h-[40px] border-r border-[var(--border)] bg-[var(--surface-2)] px-[14px] text-left font-mono text-[12.5px] font-bold whitespace-nowrap text-[var(--ink-2)]">
      {children}
    </td>
  );
}

function CellInput({
  name,
  disabled,
}: {
  name: string;
  disabled: boolean;
}) {
  const { control } = useFormContext<FormValues>();
  return (
    <td className="h-[40px] border-r border-b border-[var(--border)] p-0 last:border-r-0">
      <Controller
        control={control}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        name={name as any}
        render={({ field }) => (
          <input
            ref={field.ref}
            value={formatUzs((field.value as string) ?? "")}
            onBlur={field.onBlur}
            onChange={(e) => field.onChange(digitsOnly(e.target.value))}
            inputMode="numeric"
            placeholder="—"
            tabIndex={disabled ? -1 : 0}
            aria-hidden={disabled}
            className="h-[40px] w-full bg-transparent px-3 text-right font-mono text-[13px] tabular-nums text-[var(--ink-1)] outline-none placeholder:text-[var(--ink-4)] focus:bg-[var(--brand-primary-soft)] focus:shadow-[inset_0_0_0_1.5px_var(--brand-primary)]"
          />
        )}
      />
    </td>
  );
}
