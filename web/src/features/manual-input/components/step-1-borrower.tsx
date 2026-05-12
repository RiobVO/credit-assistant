"use client";

import { differenceInDays, differenceInMonths, parse, isValid } from "date-fns";
import { CheckCircle2, Search, TriangleAlert } from "lucide-react";
import { Controller, useFormContext } from "react-hook-form";

import { cn } from "@/lib/utils";

import { type FormValues, legalForms } from "../schema";

import { Field, FieldInput, fieldInputClass } from "./field";

export function Step1Borrower() {
  const {
    register,
    control,
    formState: { errors, touchedFields },
    watch,
  } = useFormContext<FormValues>();

  const innValue = watch("step1.inn");
  const innValid = /^\d{9}$/.test(innValue ?? "");

  const regDate = watch("step1.registrationDate");
  const apptDate = watch("step1.directorAppointedAt");

  const innErr = errors.step1?.inn?.message;
  const nameErr = errors.step1?.name?.message;
  const regErr = errors.step1?.registrationDate?.message;
  const okvedErr = errors.step1?.okvedMain?.message;
  const dirErr = errors.step1?.directorName?.message;
  const apptErr = errors.step1?.directorAppointedAt?.message;
  const addrErr = errors.step1?.registeredAddress?.message;
  const innTouched = touchedFields.step1?.inn;

  return (
    <section className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ink-1)]">
            Сведения о заёмщике
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            Юридическое лицо · резидент Республики Узбекистан
          </p>
        </div>
      </header>

      <div className="p-[22px]">
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
          {/* ИНН */}
          <Field
            label="ИНН организации"
            required
            help="9 цифр · формат ГНК Республики Узбекистан"
            error={innTouched ? innErr : undefined}
            badge={
              innValid ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-[#BFE2D2] bg-[var(--state-ok-bg)] px-[7px] py-px text-[11.5px] font-semibold text-[var(--state-ok-fg)]">
                  <CheckCircle2 className="size-3" />
                  Проверено в ГНК
                </span>
              ) : null
            }
          >
            <div className="relative flex items-center">
              <input
                {...register("step1.inn")}
                inputMode="numeric"
                maxLength={9}
                placeholder="123456789"
                className={cn(
                  fieldInputClass,
                  "pr-[38px] font-mono tracking-[0.5px]",
                  innValid &&
                    "border-[#7CC2A6] focus:shadow-[0_0_0_3px_rgba(15,138,95,0.15)]",
                )}
              />
              {innValid ? (
                <div className="pointer-events-none absolute right-[10px]">
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="var(--state-ok-fg)"
                    strokeWidth="2.2"
                  >
                    <circle
                      cx="12"
                      cy="12"
                      r="9.5"
                      fill="var(--state-ok-bg)"
                      stroke="var(--state-ok-stroke)"
                    />
                    <path d="m7.5 12.2 3 3 6-6.5" />
                  </svg>
                </div>
              ) : null}
            </div>
          </Field>

          {/* Наименование */}
          <Field
            label="Наименование компании"
            required
            help="Полное наименование согласно учредительным документам"
            error={nameErr}
          >
            <FieldInput
              {...register("step1.name")}
              placeholder='ООО «Самарканд Агро Логистика»'
              invalid={Boolean(nameErr)}
            />
          </Field>

          {/* ОПФ */}
          <Field label="Организационно-правовая форма" required>
            <Controller
              control={control}
              name="step1.legalForm"
              render={({ field }) => (
                <div className="relative">
                  <select
                    {...field}
                    className={cn(
                      fieldInputClass,
                      "appearance-none pr-9",
                    )}
                  >
                    {legalForms.map((opf) => (
                      <option key={opf.code} value={opf.code}>
                        {opf.label}
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

          {/* Дата регистрации */}
          <Field
            label="Дата государственной регистрации"
            required
            help={derivedActivityHint(regDate, "Срок деятельности")}
            error={regErr}
          >
            <FieldInput
              {...register("step1.registrationDate")}
              type="date"
              max={todayIso()}
              invalid={Boolean(regErr)}
            />
          </Field>

          {/* ОКВЭД */}
          <Field
            label="Основной ОКВЭД"
            required
            help="Код вида экономической деятельности"
            error={okvedErr}
          >
            <div className="relative flex items-center">
              <input
                {...register("step1.okvedMain")}
                placeholder="49.41 — Деятельность автомобильного грузового транспорта"
                className={cn(
                  fieldInputClass,
                  "pr-[38px] font-mono",
                )}
              />
              <Search className="pointer-events-none absolute right-[10px] size-4 text-[var(--ink-3)]" />
            </div>
          </Field>

          {/* Директор */}
          <Field
            label="Директор (Ф.И.О.)"
            required
            help="В точности как указано в выписке"
            error={dirErr}
          >
            <FieldInput
              {...register("step1.directorName")}
              placeholder="Рахимов Бекзод Алишерович"
              invalid={Boolean(dirErr)}
            />
          </Field>

          {/* Дата назначения */}
          <Field
            label="Дата назначения директора"
            required
            help={derivedActivityHint(apptDate, "Срок полномочий")}
            error={apptErr}
          >
            <FieldInput
              {...register("step1.directorAppointedAt")}
              type="date"
              min={regDate || undefined}
              max={todayIso()}
              invalid={Boolean(apptErr)}
            />
            {/* CA-039: pre-warning — формальной error нет, поле валидно,
                но смена директора <90 дней — будущий risk signal в досье. */}
            {!apptErr && isRecentDirectorAppointment(apptDate) ? (
              <div
                role="note"
                className="mt-1.5 inline-flex items-start gap-1.5 rounded-md border border-[#F1D9A6] bg-[#FFF6E5] px-2 py-1 text-[12px] text-[var(--state-warn-fg)]"
              >
                <TriangleAlert className="mt-px size-3.5 shrink-0" />
                <span>
                  Назначение менее 90 дней назад — будет учтено как сигнал риска
                </span>
              </div>
            ) : null}
          </Field>

          {/* Юридический адрес */}
          <Field
            label="Юридический адрес"
            required
            help="Согласно учредительным документам"
            error={addrErr}
            className="md:col-span-2"
          >
            <FieldInput
              {...register("step1.registeredAddress")}
              placeholder="Самарканд, ул. Регистан, 12"
              invalid={Boolean(addrErr)}
            />
          </Field>
        </div>
      </div>
    </section>
  );
}

// CA-039: «свежее» назначение директора (<90 дней) — pre-warning о будущем risk-сигнале.
// Чистая функция, экспортируется для unit-теста.
export function isRecentDirectorAppointment(
  value: string | undefined,
  thresholdDays = 90,
  now: Date = new Date(),
): boolean {
  if (!value) return false;
  const d = parse(value, "yyyy-MM-dd", new Date());
  if (!isValid(d)) return false;
  const diff = differenceInDays(now, d);
  // Будущая дата (diff<0) или старше порога — не показываем.
  return diff >= 0 && diff < thresholdDays;
}

function derivedActivityHint(value: string | undefined, prefix: string): string | undefined {
  if (!value) return undefined;
  const d = parse(value, "yyyy-MM-dd", new Date());
  if (!isValid(d)) return undefined;
  const months = differenceInMonths(new Date(), d);
  if (months < 0) return undefined;
  const years = Math.floor(months / 12);
  const remMonths = months % 12;
  const yearsLabel = pluralYears(years);
  const monthsLabel = pluralMonths(remMonths);
  if (years === 0) return `${prefix}: ${monthsLabel}`;
  if (remMonths === 0) return `${prefix}: ${yearsLabel}`;
  return `${prefix}: ${yearsLabel} ${monthsLabel}`;
}

function todayIso(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function pluralYears(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return `${n} лет`;
  if (mod10 === 1) return `${n} год`;
  if (mod10 >= 2 && mod10 <= 4) return `${n} года`;
  return `${n} лет`;
}

function pluralMonths(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return `${n} мес.`;
  if (mod10 === 1) return `${n} мес.`;
  return `${n} мес.`;
}
