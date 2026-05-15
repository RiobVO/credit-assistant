"use client";

// Phase 8: Step 3 design statement. Section card pattern (Phase 6/7 — icon-tile
// + gradient header + counter), CustomDropdown для loanTermMonths вместо
// native <select>, category pills в nested sub-block на surface-2.
//
// Три связанные section-card:
//   1. «Условия кредита» (этот файл) — Banknote icon + live counter «N/5»
//   2. DSCR Pre-score (dscr-summary.tsx) — TrendingUp + static «обновлено»
//   3. Checklist (checklist.tsx) — ClipboardCheck + counter ok/total
//
// Schema invariant: 5 required-полей в zod (loanAmount, loanTermMonths,
// loanRatePct, loanPurpose ≥20 симв, loanCategory enum). Структура form-data
// не трогается — это UI-only rewrite. Counter «N/5» обновляется по
// useWatch + 5 предикатов «filled» (см. countFilled).
//
// CA-DS24: USD-конвертация — backend ``GET /api/system/usd-rate`` (config-driven
// + env override). Loading state — пустой USD-блок в hint, fallback rate не
// показывается (честный «—» вместо stale). CBU API integration → CA-DS24b.

import { useQuery } from "@tanstack/react-query";
import { addMonths, format } from "date-fns";
import { Banknote } from "lucide-react";
import { useTranslations } from "next-intl";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { getUsdRate } from "@/lib/api";
import { cn } from "@/lib/utils";

import { CounterChip, SectionCard } from "@/components/section-card";

import { Checklist } from "./checklist";
import { CustomDropdown } from "./custom-dropdown";
import { DscrSummary } from "./dscr-summary";
import { Field, fieldInputClass } from "./field";
import {
  digitsOnly,
  formatUzs,
  hasAnyQuarterValue,
  parseAmount,
  parseRate,
  sumQuarters,
} from "../lib/finance";
import {
  type FormValues,
  loanCategories,
  loanTerms,
} from "../schema";

export function Step3Loan() {
  const t = useTranslations("accountant.manual_input");
  const {
    control,
    register,
    formState: { errors, touchedFields },
  } = useFormContext<FormValues>();

  const e = errors.step3;
  const touched = touchedFields.step3;

  const loanAmountStr = useWatch({ control, name: "step3.loanAmount" });
  const termMonths = useWatch({ control, name: "step3.loanTermMonths" });
  const ratePctStr = useWatch({ control, name: "step3.loanRatePct" });
  const purpose = useWatch({ control, name: "step3.loanPurpose" });
  const category = useWatch({ control, name: "step3.loanCategory" });

  const revenue2025 = useWatch({ control, name: "step2.revenue.y2025" });
  const profit2025 = useWatch({ control, name: "step2.netProfit.y2025" });
  // CA-033: null = «не введено ни одной cell»; 0 = «введён явный 0».
  // Различие критично для pre-score: null → neutral pill, 0 → red flag.
  const annualRevenue =
    revenue2025 && hasAnyQuarterValue(revenue2025)
      ? sumQuarters(revenue2025)
      : null;
  const annualNetProfit =
    profit2025 && hasAnyQuarterValue(profit2025)
      ? sumQuarters(profit2025)
      : null;

  const loanAmount = parseAmount(loanAmountStr ?? "");
  const ratePct = parseRate(ratePctStr ?? "");

  // CA-DS24: курс приходит с бэка. До завершения query — null → UI-блок
  // показывает default-help без USD-эквивалента (честно вместо stale rate).
  const usdRateQuery = useQuery({
    queryKey: ["usd-uzs-rate"],
    queryFn: getUsdRate,
    staleTime: 60 * 60 * 1000, // 1 час: курс меняется раз в день
  });
  const usdRate = usdRateQuery.data
    ? Number.parseFloat(usdRateQuery.data.rate)
    : null;
  const usdEquivalent =
    loanAmount > 0 && usdRate && usdRate > 0
      ? Math.round(loanAmount / usdRate)
      : 0;
  const repaymentDate =
    termMonths > 0 ? format(addMonths(new Date(), termMonths), "dd.MM.yyyy") : "—";

  const filled = countFilled({
    loanAmount: loanAmountStr ?? "",
    termMonths: termMonths ?? 0,
    ratePct: ratePctStr ?? "",
    purpose: purpose ?? "",
    category: category ?? "",
  });

  return (
    <div className="space-y-[18px]">
      <SectionCard
        icon={<Banknote className="size-[18px]" />}
        title={t("s3_section_title")}
        sub={t("s3_section_sub")}
        aux={
          <CounterChip
            filled={filled}
            total={5}
            eyebrow={t("s3_counter_filled")}
          />
        }
      >
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
          {/* Сумма кредита (col-span-2, large) */}
          <Field
            label={t("s3_amount_label")}
            required
            help={
              loanAmount > 0 && usdRate && usdRate > 0
                ? t("s3_amount_help_with_usd", {
                    usd: formatUzs(String(usdEquivalent)),
                    rate: formatUzs(String(Math.round(usdRate))),
                  })
                : t("s3_amount_help_default")
            }
            error={touched?.loanAmount ? e?.loanAmount?.message : undefined}
            className="md:col-span-2"
          >
            <div className="flex items-stretch">
              <Controller
                control={control}
                name="step3.loanAmount"
                render={({ field }) => (
                  <input
                    ref={field.ref}
                    value={formatUzs((field.value as string) ?? "")}
                    onBlur={field.onBlur}
                    onChange={(ev) => field.onChange(digitsOnly(ev.target.value))}
                    inputMode="numeric"
                    placeholder="0"
                    className={cn(
                      fieldInputClass,
                      "h-12 rounded-r-none border-r-0 text-right font-mono text-[18px] font-semibold",
                    )}
                  />
                )}
              />
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[var(--surface-2)] px-3 text-[14px] font-semibold text-[var(--ink-2)]">
                UZS
              </div>
            </div>
          </Field>

          {/* Срок — premium custom dropdown */}
          <Field
            label={t("s3_term_label")}
            required
            help={t("s3_term_help", { date: repaymentDate })}
          >
            <Controller
              control={control}
              name="step3.loanTermMonths"
              render={({ field }) => (
                <CustomDropdown<number>
                  value={field.value}
                  onChange={(next) => field.onChange(next)}
                  options={loanTerms.map((opt) => ({
                    value: opt.months,
                    label: opt.label,
                  }))}
                />
              )}
            />
          </Field>

          {/* Ставка */}
          <Field
            label={t("s3_rate_label")}
            required
            error={touched?.loanRatePct ? e?.loanRatePct?.message : undefined}
            help={t("s3_rate_help")}
          >
            <div className="flex items-stretch">
              <input
                {...register("step3.loanRatePct")}
                placeholder="18,5"
                inputMode="decimal"
                aria-invalid={Boolean(e?.loanRatePct) || undefined}
                className={cn(
                  fieldInputClass,
                  "rounded-r-none border-r-0 text-right font-mono",
                )}
              />
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[var(--surface-2)] px-3 text-[13px] font-medium text-[var(--ink-3)]">
                {t("s3_rate_suffix")}
              </div>
            </div>
            <RateBar value={ratePct} />
          </Field>

          {/* Цель + Категория (nested sub-block внутри purpose Field) */}
          <Field
            label={t("s3_purpose_label")}
            required
            error={touched?.loanPurpose ? e?.loanPurpose?.message : undefined}
            className="md:col-span-2"
          >
            <textarea
              {...register("step3.loanPurpose")}
              rows={5}
              placeholder={t("s3_purpose_placeholder")}
              aria-invalid={Boolean(e?.loanPurpose) || undefined}
              className="min-h-[120px] w-full resize-y rounded-[9px] border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-3 text-[14px] leading-[1.5] text-[var(--ink-1)] outline-none transition-colors focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)] aria-invalid:border-[var(--state-bad-fg)]"
            />
            <div className="mt-1 flex items-center justify-between">
              <span className="text-[12px] text-[var(--ink-4)]">
                {t("s3_purpose_hint")}
              </span>
              <span className="font-mono text-[11.5px] text-[var(--ink-4)]">
                {(purpose ?? "").length} / 2000
              </span>
            </div>
            <CategoryBlock />
          </Field>
        </div>
      </SectionCard>

      <DscrSummary
        loanAmount={loanAmount}
        termMonths={termMonths}
        ratePct={ratePct}
        annualRevenue={annualRevenue}
        annualNetProfit={annualNetProfit}
      />

      <Checklist />
    </div>
  );
}

// Категория — flat sub-block внутри purpose Field на surface-2 (nested).
// Визуально читается как «параметр цели», не отдельная странная плашка.
function CategoryBlock() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  return (
    <Controller
      control={control}
      name="step3.loanCategory"
      render={({ field }) => (
        <div className="mt-[10px] rounded-[11px] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-[14px]">
          <div className="mb-[10px] flex items-center gap-2">
            <span className="text-[10.5px] font-semibold tracking-[0.08em] text-[var(--ink-4)] uppercase">
              {t("s3_category_eyebrow")}
            </span>
            <span className="text-[11px] font-bold text-[var(--state-bad-fg)]">
              *
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {loanCategories.map((cat) => {
              const active = field.value === cat.code;
              return (
                <button
                  key={cat.code}
                  type="button"
                  onClick={() => field.onChange(cat.code)}
                  className={cn(
                    "rounded-full border px-[14px] py-[7px] text-[13px] transition-all",
                    active
                      ? "border-[color-mix(in_srgb,var(--brand-primary)_45%,transparent)] bg-[var(--brand-primary-soft)] font-semibold text-[var(--brand-primary-ink)]"
                      : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink-2)] hover:border-[var(--brand-primary)] hover:text-[var(--ink-1)]",
                  )}
                >
                  {cat.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    />
  );
}

// Rate-bar slider visualization (14-26% market range). Premium-feel без motion.
function RateBar({ value }: { value: number }) {
  const min = 14;
  const max = 26;
  const clamped = Math.min(Math.max(value, min), max);
  const pct = ((clamped - min) / (max - min)) * 100;
  return (
    <div className="mt-2 flex items-center gap-[14px]">
      <div className="relative h-1.5 flex-1 rounded-full bg-[var(--chart-track-light)]">
        <span
          className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-[var(--state-ok-fg)] to-[var(--brand-primary)]"
          style={{ width: `${pct}%` }}
        />
        <span
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-[var(--brand-primary)] bg-[var(--surface)] shadow-[0_1px_4px_rgba(0,0,0,0.15)]"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex w-full max-w-[200px] justify-between font-mono text-[11px] text-[var(--ink-4)]">
        <span>14%</span>
        <span>26%</span>
      </div>
    </div>
  );
}

// Counter: 5 предикатов «filled». Категория всегда truthy (default
// 'working_capital'); сумма/срок/ставка — по naturally-parsed value;
// purpose — по длине ≥20 (matches zod min(20)).
function countFilled({
  loanAmount,
  termMonths,
  ratePct,
  purpose,
  category,
}: {
  loanAmount: string;
  termMonths: number;
  ratePct: string;
  purpose: string;
  category: string;
}): number {
  let n = 0;
  if (digitsOnly(loanAmount).length > 0) n += 1;
  if (termMonths > 0) n += 1;
  if (ratePct.trim().length > 0) n += 1;
  if (purpose.trim().length >= 20) n += 1;
  if (category.length > 0) n += 1;
  return n;
}
