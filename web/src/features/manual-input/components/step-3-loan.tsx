"use client";

import { addMonths, format } from "date-fns";
import { Info } from "lucide-react";
import { useTranslations } from "next-intl";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { cn } from "@/lib/utils";

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

import { Checklist } from "./checklist";
import { DscrSummary } from "./dscr-summary";
import { Field, fieldInputClass } from "./field";

const USD_RATE_UZS = 12575;

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

  const usdEquivalent =
    loanAmount > 0 ? Math.round(loanAmount / USD_RATE_UZS) : 0;
  const repaymentDate =
    termMonths > 0 ? format(addMonths(new Date(), termMonths), "dd.MM.yyyy") : "—";

  return (
    <section className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ink-1)]">
            {t("s3_section_title")}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {t("s3_section_sub")}
          </p>
        </div>
      </header>

      <div className="p-[22px]">
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
          {/* Сумма кредита (col-2, large) */}
          <Field
            label={t("s3_amount_label")}
            required
            help={
              loanAmount > 0
                ? t("s3_amount_help_with_usd", {
                    usd: formatUzs(String(usdEquivalent)),
                    rate: formatUzs(String(USD_RATE_UZS)),
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
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[#F4F6F9] px-3 text-[14px] font-semibold text-[var(--ink-2)]">
                UZS
              </div>
            </div>
          </Field>

          {/* Срок */}
          <Field
            label={t("s3_term_label")}
            required
            help={t("s3_term_help", { date: repaymentDate })}
          >
            <Controller
              control={control}
              name="step3.loanTermMonths"
              render={({ field }) => (
                <div className="relative">
                  <select
                    value={String(field.value)}
                    onChange={(ev) => field.onChange(Number.parseInt(ev.target.value, 10))}
                    onBlur={field.onBlur}
                    className={cn(fieldInputClass, "appearance-none pr-9")}
                  >
                    {loanTerms.map((opt) => (
                      <option key={opt.months} value={opt.months}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  <span
                    aria-hidden
                    className="pointer-events-none absolute top-1/2 right-[14px] size-2 -translate-y-[70%] rotate-45 border-r-[1.5px] border-b-[1.5px] border-[var(--ink-3)]"
                  />
                </div>
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
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[#FAFBFC] px-3 text-[13px] text-[var(--ink-3)]">
                {t("s3_rate_suffix")}
              </div>
            </div>
            <RateBar value={ratePct} />
          </Field>

          {/* Цель */}
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
              className="min-h-[120px] w-full resize-y rounded-md border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-3 text-[14px] leading-[1.5] text-[var(--ink-1)] outline-none focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_rgba(30,85,201,0.15)] aria-invalid:border-[var(--state-bad-fg)]"
            />
            <div className="mt-0.5 flex items-center justify-between">
              <span className="text-[12px] text-[var(--ink-4)]">
                {t("s3_purpose_hint")}
              </span>
              <span className="font-mono text-[11.5px] text-[var(--ink-4)]">
                {(purpose ?? "").length} / 2000
              </span>
            </div>
            <CategoryPills />
          </Field>
        </div>

        <div className="my-6 h-px bg-[var(--border)]" />

        <div className="mb-1.5 flex items-end justify-between">
          <div>
            <h3 className="m-0 text-[14px] font-semibold text-[var(--ink-1)]">
              {t("s3_calc_heading")}
            </h3>
            <p className="m-0 mt-1 text-[12.5px] text-[var(--ink-3)]">
              {t("s3_calc_sub")}
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#A8C0EE] bg-[var(--brand-primary-soft)] px-[7px] py-px text-[11.5px] font-semibold text-[var(--brand-primary-hover)]">
            <Info className="size-3" />
            {t("s3_calc_updated")}
          </span>
        </div>

        <DscrSummary
          loanAmount={loanAmount}
          termMonths={termMonths}
          ratePct={ratePct}
          annualRevenue={annualRevenue}
          annualNetProfit={annualNetProfit}
        />

        <div className="my-6 h-px bg-[var(--border)]" />

        <Checklist />
      </div>
    </section>
  );
}

function CategoryPills() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  return (
    <Controller
      control={control}
      name="step3.loanCategory"
      render={({ field }) => (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-[12px] text-[var(--ink-3)]">
            {t("s3_category_label")}
          </span>
          {loanCategories.map((cat) => {
            const active = field.value === cat.code;
            return (
              <button
                key={cat.code}
                type="button"
                onClick={() => field.onChange(cat.code)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-[7px] text-[13px] transition-colors",
                  active
                    ? "border-[#A8C0EE] bg-[var(--brand-primary-soft)] font-semibold text-[var(--brand-primary-hover)]"
                    : "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[#FAFBFC]",
                )}
              >
                {cat.label}
              </button>
            );
          })}
        </div>
      )}
    />
  );
}

function RateBar({ value }: { value: number }) {
  const min = 14;
  const max = 26;
  const clamped = Math.min(Math.max(value, min), max);
  const pct = ((clamped - min) / (max - min)) * 100;
  return (
    <div className="mt-1.5 flex items-center gap-3.5">
      <div className="relative h-2 flex-1 rounded-full bg-[#EAEDF2]">
        <span
          className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-[var(--state-ok-fg)] to-[var(--brand-primary)]"
          style={{ width: `${pct}%` }}
        />
        <span
          className="absolute -top-0.5 size-3.5 -translate-x-1/2 rounded-full border-[3px] border-[var(--brand-primary)] bg-[var(--surface)] shadow-[0_1px_4px_rgba(0,0,0,0.15)]"
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

