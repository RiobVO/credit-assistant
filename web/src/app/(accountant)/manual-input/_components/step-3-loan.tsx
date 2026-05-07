"use client";

import { addMonths, format } from "date-fns";
import { Check, Info } from "lucide-react";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { cn } from "@/lib/utils";

import {
  digitsOnly,
  formatUzs,
  parseAmount,
  parseRate,
  sumQuarters,
} from "../_lib/finance";
import {
  type FormValues,
  loanCategories,
  loanTerms,
} from "../_schema";

import { DscrSummary } from "./dscr-summary";
import { Field, fieldInputClass } from "./field";

const USD_RATE_UZS = 12575;

export function Step3Loan() {
  const {
    control,
    register,
    formState: { errors, touchedFields },
  } = useFormContext<FormValues>();

  const e = errors.step3;
  const t = touchedFields.step3;

  const loanAmountStr = useWatch({ control, name: "step3.loanAmount" });
  const termMonths = useWatch({ control, name: "step3.loanTermMonths" });
  const ratePctStr = useWatch({ control, name: "step3.loanRatePct" });
  const purpose = useWatch({ control, name: "step3.loanPurpose" });

  const revenue2025 = useWatch({ control, name: "step2.revenue.y2025" });
  const profit2025 = useWatch({ control, name: "step2.netProfit.y2025" });
  const annualRevenue = revenue2025 ? sumQuarters(revenue2025) : 0;
  const annualNetProfit = profit2025 ? sumQuarters(profit2025) : 0;

  const loanAmount = parseAmount(loanAmountStr ?? "");
  const ratePct = parseRate(ratePctStr ?? "");

  const usdEquivalent =
    loanAmount > 0 ? Math.round(loanAmount / USD_RATE_UZS) : 0;
  const repaymentDate =
    termMonths > 0 ? format(addMonths(new Date(), termMonths), "dd.MM.yyyy") : "—";

  return (
    <section className="rounded-[10px] border border-[var(--ca-border)] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
            Параметры запрашиваемого кредита
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
            Все суммы — в сумах (UZS). Поля помечены звёздочкой обязательны.
          </p>
        </div>
      </header>

      <div className="p-[22px]">
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
          {/* Сумма кредита (col-2, large) */}
          <Field
            label="Сумма кредита"
            required
            help={
              loanAmount > 0
                ? `≈ ${formatUzs(String(usdEquivalent))} USD по курсу ЦБ РУз (1 USD = ${formatUzs(String(USD_RATE_UZS))} UZS)`
                : "Введите сумму запрашиваемого кредита в сумах"
            }
            error={t?.loanAmount ? e?.loanAmount?.message : undefined}
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
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--ca-border-strong)] bg-[#F4F6F9] px-3 text-[14px] font-semibold text-[var(--ca-ink-700)]">
                UZS
              </div>
            </div>
          </Field>

          {/* Срок */}
          <Field
            label="Срок кредита"
            required
            help={`Дата погашения: ${repaymentDate}`}
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
                    className="pointer-events-none absolute top-1/2 right-[14px] size-2 -translate-y-[70%] rotate-45 border-r-[1.5px] border-b-[1.5px] border-[var(--ca-ink-500)]"
                  />
                </div>
              )}
            />
          </Field>

          {/* Ставка */}
          <Field
            label="Запрошенная ставка"
            required
            error={t?.loanRatePct ? e?.loanRatePct?.message : undefined}
            help="СР ЦБ 14% · рынок 19%"
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
              <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--ca-border-strong)] bg-[#FAFBFC] px-3 text-[13px] text-[var(--ca-ink-500)]">
                % годовых
              </div>
            </div>
            <RateBar value={ratePct} />
          </Field>

          {/* Цель */}
          <Field
            label="Цель кредита"
            required
            error={t?.loanPurpose ? e?.loanPurpose?.message : undefined}
            className="md:col-span-2"
          >
            <textarea
              {...register("step3.loanPurpose")}
              rows={5}
              placeholder="Подробно опишите, на что планируется направить кредит. Указание контрагентов и контрактов помогает скорингу."
              aria-invalid={Boolean(e?.loanPurpose) || undefined}
              className="min-h-[120px] w-full resize-y rounded-md border border-[var(--ca-border-strong)] bg-white px-3 py-3 text-[14px] leading-[1.5] text-[var(--ca-ink-900)] outline-none focus:border-[var(--ca-primary-blue)] focus:shadow-[0_0_0_3px_rgba(30,85,201,0.15)] aria-invalid:border-[var(--ca-danger)]"
            />
            <div className="mt-0.5 flex items-center justify-between">
              <span className="text-[12px] text-[var(--ca-ink-400)]">
                Подробное описание помогает ускорить принятие решения
              </span>
              <span className="font-mono text-[11.5px] text-[var(--ca-ink-400)]">
                {(purpose ?? "").length} / 2000
              </span>
            </div>
            <CategoryPills />
          </Field>
        </div>

        <div className="my-6 h-px bg-[var(--ca-border)]" />

        <div className="mb-1.5 flex items-end justify-between">
          <div>
            <h3 className="m-0 text-[14px] font-semibold text-[var(--ca-ink-900)]">
              Предварительный расчёт
            </h3>
            <p className="m-0 mt-1 text-[12.5px] text-[var(--ca-ink-500)]">
              На основе введённых параметров и финансовых данных Шага 2
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[#A8C0EE] bg-[var(--ca-primary-blue-50)] px-[7px] py-px text-[11.5px] font-semibold text-[var(--ca-primary-blue-700)]">
            <Info className="size-3" />
            Расчёт обновлён
          </span>
        </div>

        <DscrSummary
          loanAmount={loanAmount}
          termMonths={termMonths}
          ratePct={ratePct}
          annualRevenue={annualRevenue}
          annualNetProfit={annualNetProfit}
        />

        <div className="my-6 h-px bg-[var(--ca-border)]" />

        <Checklist />
      </div>
    </section>
  );
}

function CategoryPills() {
  const { control } = useFormContext<FormValues>();
  return (
    <Controller
      control={control}
      name="step3.loanCategory"
      render={({ field }) => (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-[12px] text-[var(--ca-ink-500)]">
            Категория:
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
                    ? "border-[#A8C0EE] bg-[var(--ca-primary-blue-50)] font-semibold text-[var(--ca-primary-blue-700)]"
                    : "border-[var(--ca-border-strong)] bg-white text-[var(--ca-ink-700)] hover:bg-[#FAFBFC]",
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
          className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-[var(--ca-success)] to-[var(--ca-primary-blue)]"
          style={{ width: `${pct}%` }}
        />
        <span
          className="absolute -top-0.5 size-3.5 -translate-x-1/2 rounded-full border-[3px] border-[var(--ca-primary-blue)] bg-white shadow-[0_1px_4px_rgba(0,0,0,0.15)]"
          style={{ left: `${pct}%` }}
        />
      </div>
      <div className="flex w-full max-w-[200px] justify-between font-mono text-[11px] text-[var(--ca-ink-400)]">
        <span>14%</span>
        <span>26%</span>
      </div>
    </div>
  );
}

function Checklist() {
  const { control } = useFormContext<FormValues>();
  const inn = useWatch({ control, name: "step1.inn" });
  const innValid = /^\d{9}$/.test(inn ?? "");

  const revenue = useWatch({ control, name: "step2.revenue" });
  const profit = useWatch({ control, name: "step2.netProfit" });
  const filledQuarters = countFilled(revenue) + countFilled(profit);

  const totalAssets = useWatch({ control, name: "step2.totalAssets" });
  const totalLiabilities = useWatch({ control, name: "step2.totalLiabilities" });
  const balanceFilled = Boolean(totalAssets && totalLiabilities);

  return (
    <>
      <h3 className="my-3.5 text-[14px] font-semibold text-[var(--ca-ink-900)]">
        Перед отправкой на скоринг
      </h3>
      <div className="flex flex-col gap-2.5">
        <ChecklistRow done={innValid}>ИНН подтверждён в реестре ГНК</ChecklistRow>
        <ChecklistRow done={filledQuarters >= 12}>
          Финансовая отчётность за 3 года заполнена ({filledQuarters} / 24)
        </ChecklistRow>
        <ChecklistRow done={balanceFilled}>
          Активы и обязательства соответствуют форме №1
        </ChecklistRow>
        <ChecklistRow done={false}>
          Рекомендуется приложить контракт с покупателем (опционально)
        </ChecklistRow>
      </div>
    </>
  );
}

function ChecklistRow({
  done,
  children,
}: {
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2.5 text-[13px] text-[var(--ca-ink-700)]">
      <span
        className={cn(
          "grid size-[18px] flex-none place-items-center rounded border",
          done
            ? "border-[#BFE2D2] bg-[var(--ca-success-50)] text-[var(--ca-success)]"
            : "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--ca-warning)]",
        )}
      >
        {done ? (
          <Check className="size-2.5" />
        ) : (
          <span className="text-[12px] font-bold">!</span>
        )}
      </span>
      {children}
    </div>
  );
}

function countFilled(year: FormValues["step2"]["revenue"] | undefined): number {
  if (!year) return 0;
  let n = 0;
  for (const yKey of ["y2023", "y2024", "y2025"] as const) {
    const y = year[yKey];
    for (const q of ["q1", "q2", "q3", "q4"] as const) {
      if (y?.[q]) n += 1;
    }
  }
  return n;
}
