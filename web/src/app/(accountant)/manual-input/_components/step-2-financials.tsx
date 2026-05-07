"use client";

import { Controller, useFormContext, useWatch } from "react-hook-form";

import { cn } from "@/lib/utils";

import {
  computeDebtToAssets,
  computeEquity,
  digitsOnly,
  formatUzs,
  parseAmount,
} from "../_lib/finance";
import type { FormValues } from "../_schema";

import { Field, fieldInputClass } from "./field";
import { FinancialTable } from "./financial-table";

export function Step2Financials() {
  return (
    <div className="space-y-[18px]">
      <Card
        title="Выручка по кварталам"
        sub="Поквартальная динамика за 3 года · все суммы в UZS, без копеек"
      >
        <FinancialTable basePath="step2.revenue" variant="revenue" />
      </Card>

      <Card
        title="Чистая прибыль по кварталам"
        sub="После налогообложения · UZS"
      >
        <FinancialTable basePath="step2.netProfit" variant="netProfit" />
      </Card>

      <Card
        title="Прочие финансовые показатели"
        sub="Годовые значения по последнему отчётному периоду (2025 г.)"
      >
        <AnnualFields />
      </Card>
    </div>
  );
}

function Card({
  title,
  sub,
  children,
}: {
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[10px] border border-[var(--ca-border)] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
            {title}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
            {sub}
          </p>
        </div>
      </header>
      <div className="p-[22px]">{children}</div>
    </section>
  );
}

function AnnualFields() {
  const {
    control,
    formState: { errors, touchedFields },
  } = useFormContext<FormValues>();

  const e = errors.step2;
  const t = touchedFields.step2;

  return (
    <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
      <UzsField
        name="step2.vatDeclared"
        label="НДС задекларированный (за год)"
        help="По данным деклараций НДС за 2025 г."
        error={t?.vatDeclared ? e?.vatDeclared?.message : undefined}
      />
      <UzsField
        name="step2.taxesPaid"
        label="Налоги уплаченные (за год)"
        help="Совокупная сумма уплаченных налогов"
        error={t?.taxesPaid ? e?.taxesPaid?.message : undefined}
      />
      <UzsField
        name="step2.totalAssets"
        label="Активы итого (на 31.12.2025)"
        help="По бухгалтерскому балансу, форма №1"
        error={t?.totalAssets ? e?.totalAssets?.message : undefined}
      />
      <UzsField
        name="step2.totalLiabilities"
        label="Обязательства итого (на 31.12.2025)"
        help="Краткосрочные + долгосрочные обязательства"
        error={t?.totalLiabilities ? e?.totalLiabilities?.message : undefined}
      />

      <ComputedRow control={control} />
    </div>
  );
}

function UzsField({
  name,
  label,
  help,
  error,
}: {
  name: "step2.vatDeclared" | "step2.taxesPaid" | "step2.totalAssets" | "step2.totalLiabilities";
  label: string;
  help: string;
  error?: string;
}) {
  const { control } = useFormContext<FormValues>();
  return (
    <Field label={label} required help={help} error={error}>
      <div className="flex items-stretch">
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <input
              ref={field.ref}
              value={formatUzs((field.value as string) ?? "")}
              onBlur={field.onBlur}
              onChange={(e) => field.onChange(digitsOnly(e.target.value))}
              inputMode="numeric"
              placeholder="0"
              aria-invalid={Boolean(error) || undefined}
              className={cn(
                fieldInputClass,
                "rounded-r-none border-r-0 text-right font-mono",
                error &&
                  "border-[var(--ca-danger)] focus:border-[var(--ca-danger)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
              )}
            />
          )}
        />
        <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--ca-border-strong)] bg-[#FAFBFC] px-3 text-[13px] text-[var(--ca-ink-500)]">
          UZS
        </div>
      </div>
    </Field>
  );
}

function ComputedRow({
  control,
}: {
  control: import("react-hook-form").Control<FormValues>;
}) {
  const assets = useWatch({ control, name: "step2.totalAssets" });
  const liabilities = useWatch({ control, name: "step2.totalLiabilities" });

  const a = parseAmount(assets ?? "");
  const l = parseAmount(liabilities ?? "");
  const da = computeDebtToAssets(l, a);
  const equity = computeEquity(a, l);
  const daTone = a === 0 ? "neutral" : da <= 0.55 ? "good" : "warn";

  return (
    <div className="md:col-span-2">
      <ComputedBox
        keyLabel="Расчётный коэффициент D/A"
        sub="Обязательства ÷ Активы · норма для отрасли ≤ 0.55"
        value={a === 0 ? "—" : da.toFixed(2)}
        tone={daTone}
      />
      <div className="h-2.5" />
      <ComputedBox
        keyLabel="Собственный капитал (расч.)"
        sub="Активы − Обязательства"
        value={equity > 0 ? `${formatUzs(String(equity))} UZS` : "—"}
        tone="neutral"
      />
    </div>
  );
}

function ComputedBox({
  keyLabel,
  sub,
  value,
  tone,
}: {
  keyLabel: string;
  sub: string;
  value: string;
  tone: "good" | "warn" | "neutral";
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-dashed border-[var(--ca-border-strong)] bg-[#FAFBFC] px-[14px] py-3">
      <div>
        <div className="text-[12px] tracking-[0.6px] text-[var(--ca-ink-500)] uppercase">
          {keyLabel}
        </div>
        <div className="mt-0.5 text-[12px] text-[var(--ca-ink-400)]">{sub}</div>
      </div>
      <div
        className={cn(
          "font-mono text-[14px] font-semibold",
          tone === "good" && "text-[var(--ca-success)]",
          tone === "warn" && "text-[var(--ca-warning)]",
          tone === "neutral" && "text-[var(--ca-ink-900)]",
        )}
      >
        {value}
      </div>
    </div>
  );
}
