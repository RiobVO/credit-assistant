"use client";

import { Controller, useFormContext, useWatch } from "react-hook-form";

import {
  computeCagrPct,
  computeMarginPct,
  digitsOnly,
  formatUzs,
  yearTotal,
} from "../lib/finance";
import type { FormValues } from "../schema";

type SectionPath = "step2.revenue" | "step2.netProfit";

const QUARTERS = ["q1", "q2", "q3", "q4"] as const;
const YEARS = [2023, 2024, 2025] as const;

type YearKey = `y${(typeof YEARS)[number]}`;

export function FinancialTable({
  basePath,
  variant,
}: {
  basePath: SectionPath;
  variant: "revenue" | "netProfit";
}) {
  const { control } = useFormContext<FormValues>();
  const watched = useWatch({
    control,
    name: basePath,
  });

  return (
    <div className="overflow-hidden rounded-lg border border-r-0 border-b-0 border-[var(--border)]">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            <Th first>Период</Th>
            <Th>Q1</Th>
            <Th>Q2</Th>
            <Th>Q3</Th>
            <Th>Q4</Th>
            <Th>Итого за год</Th>
          </tr>
        </thead>
        <tbody>
          {YEARS.map((year) => {
            const yKey = `y${year}` as YearKey;
            // CA-027: total = sum квартальных, либо annual (если quarters пустые).
            const total = watched ? yearTotal(watched[yKey]) : 0;
            return (
              <tr key={year}>
                <FirstCell>{year} г.</FirstCell>
                {QUARTERS.map((q) => (
                  <CellInput
                    key={q}
                    name={`${basePath}.${yKey}.${q}` as const}
                  />
                ))}
                <ReadOnlyTotalCell value={total} />
              </tr>
            );
          })}
        </tbody>
        <Footer variant={variant} watched={watched} />
      </table>
    </div>
  );
}

function Th({ children, first }: { children: React.ReactNode; first?: boolean }) {
  return (
    <th
      className={`border-r border-t border-b border-[var(--border)] bg-[#F4F6F9] px-3 py-2.5 text-[12px] font-semibold tracking-[0.5px] text-[var(--ink-2)] uppercase ${
        first
          ? "rounded-tl-lg border-l text-left"
          : "rounded-tl-none text-right"
      }`}
    >
      {children}
    </th>
  );
}

function FirstCell({ children }: { children: React.ReactNode }) {
  return (
    <td className="h-10 border-r border-b border-l border-[var(--border)] bg-[#FAFBFC] px-[14px] py-0 text-left font-medium whitespace-nowrap text-[var(--ink-2)]">
      {children}
    </td>
  );
}

function CellInput({ name }: { name: string }) {
  const { control } = useFormContext<FormValues>();
  return (
    <td className="h-10 border-r border-b border-[var(--border)] p-0">
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
            className="h-10 w-full bg-transparent px-3 text-right font-mono text-[13px] text-[var(--ink-1)] outline-none focus:bg-[#F4F8FF] focus:shadow-[inset_0_0_0_2px_var(--brand-primary)]"
          />
        )}
      />
    </td>
  );
}

function ReadOnlyTotalCell({ value }: { value: number }) {
  return (
    <td className="h-10 border-r border-b border-[var(--border)] p-0">
      <input
        readOnly
        value={value > 0 ? formatUzs(String(value)) : ""}
        placeholder="—"
        className="h-10 w-full bg-[#FAFBFC] px-3 text-right font-mono text-[13px] font-semibold text-[var(--ink-2)] outline-none"
      />
    </td>
  );
}

function Footer({
  variant,
  watched,
}: {
  variant: "revenue" | "netProfit";
  watched:
    | FormValues["step2"]["revenue"]
    | FormValues["step2"]["netProfit"]
    | undefined;
}) {
  if (!watched) return null;
  // Footer-агрегаты тоже учитывают annual-fallback (CA-027).
  const total2023 = yearTotal(watched.y2023);
  const total2025 = yearTotal(watched.y2025);

  if (variant === "revenue") {
    const cagr = computeCagrPct(total2023, total2025, 2);
    return (
      <tfoot>
        <tr>
          <td className="rounded-bl-lg border-r border-b border-l border-t-[1px] border-[var(--border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-left font-semibold text-[var(--ink-2)]">
            CAGR 2023→2025
            <RatioPill tone={cagrTone(cagr)}>{formatRatioPct(cagr)}</RatioPill>
          </td>
          <td
            colSpan={4}
            className="border-r border-b border-t-[1px] border-[var(--border-strong)] bg-[#F4F6F9] px-3 py-2.5 pl-[14px] text-left font-medium text-[var(--ink-3)]"
          >
            Совокупный среднегодовой темп роста выручки
          </td>
          <RatioTotalCell />
        </tr>
      </tfoot>
    );
  }

  // Margin footer: net profit / revenue for 2025. CA-034: pill в col1
  // (как у CAGR), col6 = "—" — маржа коэффициент, не годовая сумма.
  return (
    <tfoot>
      <tr>
        <td className="rounded-bl-lg border-r border-b border-l border-t-[1px] border-[var(--border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-left font-semibold text-[var(--ink-2)]">
          Маржа 2025
          <MarginPill />
        </td>
        <td
          colSpan={4}
          className="border-r border-b border-t-[1px] border-[var(--border-strong)] bg-[#F4F6F9] px-3 py-2.5 pl-[14px] text-left font-medium text-[var(--ink-3)]"
        >
          Рентабельность по чистой прибыли
        </td>
        <RatioTotalCell />
      </tr>
    </tfoot>
  );
}

function MarginPill() {
  const { control } = useFormContext<FormValues>();
  const revenue = useWatch({ control, name: "step2.revenue.y2025" });
  const profit = useWatch({ control, name: "step2.netProfit.y2025" });
  const r = revenue ? yearTotal(revenue) : 0;
  const p = profit ? yearTotal(profit) : 0;
  const margin = computeMarginPct(p, r);
  return <RatioPill tone={cagrTone(margin)}>{formatRatioPct(margin)}</RatioPill>;
}

function RatioTotalCell() {
  return (
    <td className="rounded-br-lg border-r border-b border-t-[1px] border-[var(--border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-right font-mono text-[13px] font-semibold text-[var(--ink-3)]">
      —
    </td>
  );
}

function formatRatioPct(value: number | null): string {
  if (value == null) return "N/A";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function cagrTone(value: number | null): "success" | "danger" | "neutral" {
  if (value == null) return "neutral";
  return value > 0 ? "success" : "danger";
}

function RatioPill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "success" | "danger" | "neutral";
}) {
  const palette =
    tone === "success"
      ? "bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
      : tone === "danger"
        ? "bg-[#FCE7E5] text-[var(--state-bad-fg)]"
        : "bg-[#F4F6F9] text-[var(--ink-3)] border border-[var(--border)]";
  return (
    <span
      className={`ml-2 rounded-full px-1.5 py-px font-mono text-[11.5px] font-semibold ${palette}`}
    >
      {children}
    </span>
  );
}
