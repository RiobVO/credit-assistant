"use client";

import { Controller, useFormContext, useWatch } from "react-hook-form";

import {
  computeCagrPct,
  computeMarginPct,
  digitsOnly,
  formatUzs,
  parseAmount,
} from "../_lib/finance";
import type { FormValues } from "../_schema";

type SectionPath = "step2.revenue" | "step2.netProfit";

const QUARTERS = ["q1", "q2", "q3", "q4"] as const;
const YEARS = [2023, 2024, 2025] as const;

type QuarterKey = (typeof QUARTERS)[number];
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
    <div className="overflow-hidden rounded-lg border border-r-0 border-b-0 border-[var(--ca-border)]">
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
            const yearTotal = watched
              ? sumYear(watched[yKey])
              : 0;
            return (
              <tr key={year}>
                <FirstCell>{year} г.</FirstCell>
                {QUARTERS.map((q) => (
                  <CellInput
                    key={q}
                    name={`${basePath}.${yKey}.${q}` as const}
                  />
                ))}
                <ReadOnlyTotalCell value={yearTotal} />
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
      className={`border-r border-t border-b border-[var(--ca-border)] bg-[#F4F6F9] px-3 py-2.5 text-[12px] font-semibold tracking-[0.5px] text-[var(--ca-ink-700)] uppercase ${
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
    <td className="h-10 border-r border-b border-l border-[var(--ca-border)] bg-[#FAFBFC] px-[14px] py-0 text-left font-medium whitespace-nowrap text-[var(--ca-ink-700)]">
      {children}
    </td>
  );
}

function CellInput({ name }: { name: string }) {
  const { control } = useFormContext<FormValues>();
  return (
    <td className="h-10 border-r border-b border-[var(--ca-border)] p-0">
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
            className="h-10 w-full bg-transparent px-3 text-right font-mono text-[13px] text-[var(--ca-ink-900)] outline-none focus:bg-[#F4F8FF] focus:shadow-[inset_0_0_0_2px_var(--ca-primary-blue)]"
          />
        )}
      />
    </td>
  );
}

function ReadOnlyTotalCell({ value }: { value: number }) {
  return (
    <td className="h-10 border-r border-b border-[var(--ca-border)] p-0">
      <input
        readOnly
        value={value > 0 ? formatUzs(String(value)) : ""}
        placeholder="—"
        className="h-10 w-full bg-[#FAFBFC] px-3 text-right font-mono text-[13px] font-semibold text-[var(--ca-ink-700)] outline-none"
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
  const total2023 = sumYear(watched.y2023);
  const total2024 = sumYear(watched.y2024);
  const total2025 = sumYear(watched.y2025);
  const totalAll = total2023 + total2024 + total2025;

  if (variant === "revenue") {
    const cagr = computeCagrPct(total2023, total2025, 2);
    const cagrSign = cagr > 0 ? "+" : "";
    return (
      <tfoot>
        <tr>
          <td className="rounded-bl-lg border-r border-b border-l border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-left font-semibold text-[var(--ca-ink-700)]">
            CAGR 2023→2025
            <DeltaPill positive={cagr > 0}>
              {cagrSign}
              {cagr.toFixed(1)}%
            </DeltaPill>
          </td>
          <td
            colSpan={4}
            className="border-r border-b border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 pl-[14px] text-left font-medium text-[var(--ca-ink-500)]"
          >
            Совокупный среднегодовой темп роста выручки
          </td>
          <td className="rounded-br-lg border-r border-b border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-right font-mono text-[13px] font-semibold text-[var(--ca-ink-900)]">
            {totalAll > 0 ? formatUzs(String(totalAll)) : "—"}
          </td>
        </tr>
      </tfoot>
    );
  }

  // Margin footer: net profit / revenue for 2025
  return (
    <tfoot>
      <tr>
        <td className="rounded-bl-lg border-r border-b border-l border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-left font-semibold text-[var(--ca-ink-700)]">
          Маржа 2025
        </td>
        <td
          colSpan={4}
          className="border-r border-b border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 pl-[14px] text-left font-medium text-[var(--ca-ink-500)]"
        >
          Рентабельность по чистой прибыли
        </td>
        <td className="rounded-br-lg border-r border-b border-t-[1px] border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 py-2.5 text-right font-mono text-[13px] font-semibold text-[var(--ca-ink-900)]">
          <MarginCell />
        </td>
      </tr>
    </tfoot>
  );
}

function MarginCell() {
  const { control } = useFormContext<FormValues>();
  const revenue = useWatch({ control, name: "step2.revenue.y2025" });
  const profit = useWatch({ control, name: "step2.netProfit.y2025" });
  const r = revenue ? sumYear(revenue) : 0;
  const p = profit ? sumYear(profit) : 0;
  if (r === 0) return <>—</>;
  return <>{computeMarginPct(p, r).toFixed(1)}%</>;
}

function sumYear(y: Record<QuarterKey, string> | undefined): number {
  if (!y) return 0;
  return parseAmount(y.q1) + parseAmount(y.q2) + parseAmount(y.q3) + parseAmount(y.q4);
}

function DeltaPill({
  children,
  positive,
}: {
  children: React.ReactNode;
  positive: boolean;
}) {
  return (
    <span
      className={`ml-2 rounded-full px-1.5 py-px font-mono text-[11.5px] font-semibold ${
        positive
          ? "bg-[var(--ca-success-50)] text-[var(--ca-success)]"
          : "bg-[#FCE7E5] text-[var(--ca-danger)]"
      }`}
    >
      {children}
    </span>
  );
}
