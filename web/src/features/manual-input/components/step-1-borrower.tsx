"use client";

import { differenceInDays, parse, isValid } from "date-fns";
import { CheckCircle2, Search, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { Controller, useFormContext } from "react-hook-form";

import { cn } from "@/lib/utils";

import { formatBusinessAge } from "../lib/duration";
import { type FormValues, legalForms } from "../schema";

import { Field, FieldInput, fieldInputClass } from "./field";

export function Step1Borrower() {
  const t = useTranslations("accountant.manual_input");
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
            {t("s1_section_title")}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {t("s1_section_sub")}
          </p>
        </div>
      </header>

      <div className="p-[22px]">
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
          {/* ИНН */}
          <Field
            label={t("s1_inn_label")}
            required
            help={t("s1_inn_help")}
            error={innTouched ? innErr : undefined}
            badge={
              innValid ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-[#BFE2D2] bg-[var(--state-ok-bg)] px-[7px] py-px text-[11.5px] font-semibold text-[var(--state-ok-fg)]">
                  <CheckCircle2 className="size-3" />
                  {t("s1_inn_badge_verified")}
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
            label={t("s1_name_label")}
            required
            help={t("s1_name_help")}
            error={nameErr}
          >
            <FieldInput
              {...register("step1.name")}
              placeholder={t("s1_name_placeholder")}
              invalid={Boolean(nameErr)}
            />
          </Field>

          {/* ОПФ */}
          <Field label={t("s1_opf_label")} required>
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
            label={t("s1_reg_label")}
            required
            help={formatBusinessAgeHint(regDate, t("s1_reg_age_prefix"))}
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
            label={t("s1_okved_label")}
            required
            help={t("s1_okved_help")}
            error={okvedErr}
          >
            <div className="relative flex items-center">
              <input
                {...register("step1.okvedMain")}
                placeholder={t("s1_okved_placeholder")}
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
            label={t("s1_director_label")}
            required
            help={t("s1_director_help")}
            error={dirErr}
          >
            <FieldInput
              {...register("step1.directorName")}
              placeholder={t("s1_director_placeholder")}
              invalid={Boolean(dirErr)}
            />
          </Field>

          {/* Дата назначения */}
          <Field
            label={t("s1_appt_label")}
            required
            help={formatBusinessAgeHint(apptDate, t("s1_appt_age_prefix"))}
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
                <span>{t("s1_recent_director_warning")}</span>
              </div>
            ) : null}
          </Field>

          {/* Юридический адрес */}
          <Field
            label={t("s1_address_label")}
            required
            help={t("s1_address_help")}
            error={addrErr}
            className="md:col-span-2"
          >
            <FieldInput
              {...register("step1.registeredAddress")}
              placeholder={t("s1_address_placeholder")}
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

function formatBusinessAgeHint(
  value: string | undefined,
  prefix: string,
): string | undefined {
  const age = formatBusinessAge(value);
  return age ? `${prefix}: ${age}` : undefined;
}

function todayIso(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

