"use client";

import { useQuery } from "@tanstack/react-query";
import { differenceInDays, isValid, parse } from "date-fns";
import {
  Building2,
  CheckCircle2,
  ChevronDown,
  Loader2,
  TriangleAlert,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Controller,
  useFormContext,
  useWatch,
  type Control,
} from "react-hook-form";

import { getOkvedCatalog, type OkvedItemDto } from "@/lib/api";
import { cn } from "@/lib/utils";

import { formatBusinessAge } from "../lib/duration";
import { type FormValues, type Step1Values } from "../schema";

import { DatePicker } from "./date-picker";
import { Field, FieldInput } from "./field";
import { GnkCertificateUpload } from "./gnk-certificate-upload";

// Phase 6 Step 1 design statement: section-card в стиле Phase 4 (leading
// icon-tile + counter), ИНН 3-state (idle/checking/verified) с mock GNK
// lookup, OKVED autocomplete (источник — backend catalog GET /api/system/okved,
// CA-DS17), ОПФ как segmented radio, custom date picker для дат (без native
// <input type="date">).
//
// Сохранено: CA-038 (≥15 симв + цифра), CA-039 (isRecentDirectorAppointment
// + amber warning), CA-058 prefill через sessionStorage.

const CHECK_DELAY_MS = 700;

const OPF_OPTIONS = [
  { code: "llc" as const, shortKey: "opf_llc_short" },
  { code: "ie" as const, shortKey: "opf_ie_short" },
  { code: "jsc" as const, shortKey: "opf_jsc_short" },
];

export function Step1Borrower() {
  const t = useTranslations("accountant.manual_input");
  const {
    register,
    control,
    formState: { errors, touchedFields },
    setValue,
  } = useFormContext<FormValues>();

  // Чтобы counter (заполнено N/8) обновлялся живо, держим всю под-форму Шага 1
  // в watch. Перерасчёт счётчика дёшев — 8 boolean-проверок.
  const step1 = useWatch({ control, name: "step1" });

  const innErr = errors.step1?.inn?.message;
  const innTouched = touchedFields.step1?.inn;
  const nameErr = errors.step1?.name?.message;
  const regErr = errors.step1?.registrationDate?.message;
  const okvedErr = errors.step1?.okvedMain?.message;
  const dirErr = errors.step1?.directorName?.message;
  const apptErr = errors.step1?.directorAppointedAt?.message;
  const addrErr = errors.step1?.registeredAddress?.message;

  const filledCount = useMemo(() => countFilled(step1), [step1]);

  // Bound для date-picker'а назначения директора — не раньше регистрации.
  const apptMin = useMemo(() => parseIsoSafe(step1?.registrationDate), [step1?.registrationDate]);

  return (
    <section className="rounded-[14px] border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <header className="grid grid-cols-[40px_1fr_auto] items-center gap-[14px] border-b border-[var(--border)] bg-gradient-to-b from-white to-[var(--surface-2)] px-[22px] py-[16px]">
        <div className="grid size-9 place-items-center rounded-[10px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]">
          <Building2 className="size-[18px]" />
        </div>
        <div>
          <h2 className="m-0 text-[15px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
            {t("s1_section_title")}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {t("s1_section_sub")}
          </p>
        </div>
        <div className="text-right">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-4)]">
            {t("s1_filled_label")}
          </div>
          <div className="mt-1 flex items-center justify-end gap-1.5">
            <div className="relative h-1 w-[60px] overflow-hidden rounded-[2px] bg-[var(--surface-3)]">
              <div
                className="absolute inset-y-0 left-0 rounded-[2px] bg-[var(--brand-primary)] transition-[width] duration-[240ms]"
                style={{ width: `${(filledCount / 8) * 100}%` }}
              />
            </div>
            <span className="font-mono text-[11.5px] font-bold text-[var(--brand-primary)] tabular-nums">
              {t("s1_filled_value", { filled: filledCount, total: 8 })}
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] p-[22px] md:grid-cols-2">
        {/* ИНН */}
        <Field
          label={t("s1_inn_label")}
          required
          error={innTouched ? innErr : undefined}
        >
          <Controller
            control={control}
            name="step1.inn"
            render={({ field }) => (
              <InnInput
                value={field.value ?? ""}
                onChange={field.onChange}
                onBlur={field.onBlur}
                invalid={Boolean(innTouched && innErr)}
              />
            )}
          />
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

        {/* ОПФ — segmented */}
        <Field
          label={t("s1_opf_label")}
          required
          help={t("s1_opf_help")}
        >
          <Controller
            control={control}
            name="step1.legalForm"
            render={({ field }) => (
              <OpfSegmented value={field.value} onChange={field.onChange} />
            )}
          />
        </Field>

        {/* Дата регистрации */}
        <Field
          label={t("s1_reg_label")}
          required
          help={formatBusinessAgeHint(step1?.registrationDate, t("s1_reg_age_prefix"))}
          error={regErr}
        >
          <Controller
            control={control}
            name="step1.registrationDate"
            render={({ field }) => (
              <DatePicker
                value={field.value || undefined}
                onChange={(iso) => {
                  field.onChange(iso ?? "");
                  // Если новая регистрация позже текущего назначения директора —
                  // чистим назначение, чтобы пользователь не оставил невалидный
                  // refine ("назначение раньше регистрации" из schema).
                  const appt = parseIsoSafe(step1?.directorAppointedAt);
                  const reg = parseIsoSafe(iso);
                  if (appt && reg && appt < reg) {
                    setValue("step1.directorAppointedAt", "", { shouldDirty: true });
                  }
                }}
                max={new Date()}
                invalid={Boolean(regErr)}
                placeholder={t("s1_date_placeholder")}
                ariaLabel={t("s1_reg_label")}
              />
            )}
          />
        </Field>

        {/* ОКВЭД autocomplete */}
        <Field
          label={t("s1_okved_label")}
          required
          help={t("s1_okved_help")}
          error={okvedErr}
        >
          <Controller
            control={control}
            name="step1.okvedMain"
            render={({ field }) => (
              <OkvedAutocomplete
                value={field.value ?? ""}
                onChange={field.onChange}
                onBlur={field.onBlur}
                invalid={Boolean(okvedErr)}
              />
            )}
          />
          {/* ADR-0024 Session 3: conditional block — показывается только когда
              backend знает дату смены ОКЭД (через парсер/ORM, prefill из
              «Пересобрать с дополнениями»). В brand-new dossier flow hidden. */}
          {step1?.okvedMainChangedAt ? (
            <OkedChangedByOwnerBlock
              date={step1.okvedMainChangedAt}
              control={control}
            />
          ) : null}
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

        {/* Дата назначения директора */}
        <Field
          label={t("s1_appt_label")}
          required
          error={apptErr}
        >
          <Controller
            control={control}
            name="step1.directorAppointedAt"
            render={({ field }) => (
              <DatePicker
                value={field.value || undefined}
                onChange={(iso) => field.onChange(iso ?? "")}
                max={new Date()}
                min={apptMin ?? undefined}
                invalid={Boolean(apptErr)}
                placeholder={t("s1_date_placeholder")}
                ariaLabel={t("s1_appt_label")}
              />
            )}
          />
          {/* CA-039: amber pre-warning — формальной error нет, поле валидно. */}
          {!apptErr && isRecentDirectorAppointment(step1?.directorAppointedAt) ? (
            <DirectorRecentWarning />
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

        {/* T0.3: ГНК-справка (manual upload, Phase A, CA-003). Optional —
            показывается только когда ИНН валиден (9 цифр). Не блокирует submit. */}
        <div className="md:col-span-2">
          <GnkCertificateUpload
            inn={(step1?.inn ?? "").replace(/\D/g, "")}
            innValid={(step1?.inn ?? "").replace(/\D/g, "").length === 9}
          />
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────
// ИНН 3-state input
// ─────────────────────────────────────────────────────────────────

type InnState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "verified"; summaryKey: "s1_inn_summary_mock" }
  | { kind: "invalid" };

export function InnInput({
  value,
  onChange,
  onBlur,
  invalid,
}: {
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  invalid: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  const [state, setState] = useState<InnState>({ kind: "idle" });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // При очистке поля или нового ввода сбрасываем state. verified остаётся
  // только пока value неизменен; при правке возвращаемся в idle до blur.
  // ESLint react-hooks/set-state-in-effect запрещает синхронный setState в
  // effect body — обходим через macrotask (setTimeout 0), консистентно с
  // CA-066 паттерном в HotlinePrimaryCard.
  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const t = setTimeout(() => setState({ kind: "idle" }), 0);
    return () => clearTimeout(t);
  }, [value]);

  const handleBlur = useCallback(() => {
    onBlur();
    if (!value) {
      setState({ kind: "idle" });
      return;
    }
    if (!/^\d{9}$/.test(value)) {
      setState({ kind: "invalid" });
      return;
    }
    // Skip re-checking если уже verified для текущего value. useEffect [value]
    // сбрасывает state в idle на любое изменение → если мы здесь и
    // state.kind === "verified", значит value не менялся, повторный blur
    // не должен фантомно «проверять заново» с visible flash spinner-а.
    if (state.kind === "verified") return;
    setState({ kind: "checking" });
    // Mock GNK lookup. TODO[CA-003]: реальный запрос /api/system/gnk/{inn}.
    timerRef.current = setTimeout(() => {
      setState({ kind: "verified", summaryKey: "s1_inn_summary_mock" });
    }, CHECK_DELAY_MS);
  }, [onBlur, value, state.kind]);

  const verified = state.kind === "verified";

  return (
    <div>
      <div className="relative flex items-center">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 9))}
          onBlur={handleBlur}
          inputMode="numeric"
          maxLength={9}
          placeholder="123456789"
          aria-invalid={invalid || undefined}
          className={cn(
            "h-10 w-full rounded-[9px] border bg-[var(--surface)] pr-[38px] pl-3 font-mono text-[14px] tracking-[0.5px] text-[var(--ink-1)] outline-none transition-colors placeholder:text-[var(--ink-4)]",
            "border-[var(--border-strong)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]",
            verified &&
              "border-[var(--state-ok-border)] focus:border-[var(--state-ok-fg)] focus:shadow-[0_0_0_3px_rgba(15,138,95,0.15)]",
            invalid &&
              "border-[var(--state-bad-fg)] focus:border-[var(--state-bad-fg)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
          )}
        />
        <div className="pointer-events-none absolute right-[10px] flex items-center">
          {state.kind === "checking" ? (
            <Loader2 className="size-4 animate-spin text-[var(--brand-primary-ink)]" />
          ) : verified ? (
            <CheckCircle2 className="size-[18px] text-[var(--state-ok-fg)]" />
          ) : null}
        </div>
      </div>
      <div className="mt-2 flex min-h-[22px] items-center gap-[10px]">
        {state.kind === "idle" ? (
          <span className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-[3px] text-[11.5px] font-semibold text-[var(--ink-4)]">
            {t("s1_inn_state_idle")}
          </span>
        ) : null}
        {state.kind === "checking" ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--brand-primary-soft)] bg-[var(--brand-primary-soft)] px-2 py-[3px] text-[11.5px] font-semibold text-[var(--brand-primary-ink)]">
            <Loader2 className="size-3 animate-spin" />
            {t("s1_inn_state_checking")}
          </span>
        ) : null}
        {state.kind === "verified" ? (
          <>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] px-2 py-[3px] text-[11.5px] font-semibold text-[var(--state-ok-fg)]">
              <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
              {t("s1_inn_state_verified")}
            </span>
            <span className="text-[11.5px] text-[var(--ink-3)]">
              {t(state.summaryKey)}
            </span>
          </>
        ) : null}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ОПФ segmented
// ─────────────────────────────────────────────────────────────────

function OpfSegmented({
  value,
  onChange,
}: {
  value: Step1Values["legalForm"];
  onChange: (v: Step1Values["legalForm"]) => void;
}) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      role="radiogroup"
      className="grid grid-cols-3 gap-1.5 rounded-[10px] border border-[var(--border-strong)] bg-[var(--surface)] p-1"
    >
      {OPF_OPTIONS.map((opt) => {
        const active = opt.code === value;
        return (
          <button
            key={opt.code}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(opt.code)}
            className={cn(
              "h-8 rounded-[7px] text-[12.5px] font-semibold transition-colors",
              active
                ? "bg-[var(--brand-primary)] text-white shadow-[0_2px_8px_-2px_var(--brand-primary-ring)]"
                : "text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]",
            )}
          >
            {t(opt.shortKey)}
          </button>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ОКВЭД autocomplete
// ─────────────────────────────────────────────────────────────────

export function OkvedAutocomplete({
  value,
  onChange,
  onBlur,
  invalid,
}: {
  value: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  invalid: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const listboxId = "okved-listbox";

  // CA-DS17: catalog грузится один раз на mount. staleTime=∞ — reference data,
  // обновление только через restart api контейнера. Hydration-safe: queryFn
  // не вызывается на сервере (React Query SSR-friendly defaults).
  const catalogQuery = useQuery({
    queryKey: ["okved-catalog"],
    queryFn: getOkvedCatalog,
    staleTime: Infinity,
    gcTime: Infinity,
  });
  // Стабильная reference (избегаем re-create массива при каждом рендере —
  // иначе useMemo ниже теряет смысл, react-hooks/exhaustive-deps warning).
  const catalog = useMemo<OkvedItemDto[]>(
    () => catalogQuery.data?.items ?? [],
    [catalogQuery.data],
  );

  // CA-DS17: выбираем full label по локали — готовность к runtime switcher
  // (CA-DS29). Сейчас locale статичен через NEXT_PUBLIC_LOCALE, но useLocale()
  // вернёт правильное значение когда switcher появится.
  const labelFor = useCallback(
    (item: OkvedItemDto) => (locale === "uz" ? item.full_uz : item.full_ru),
    [locale],
  );

  const filtered = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter(
      (o) =>
        o.code.startsWith(q) ||
        labelFor(o).toLowerCase().includes(q),
    );
  }, [value, catalog, labelFor]);

  // См. комментарий в InnInput — обход react-hooks/set-state-in-effect.
  useEffect(() => {
    const t = setTimeout(() => setHighlight(0), 0);
    return () => clearTimeout(t);
  }, [value]);

  // Click outside.
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      const node = e.target as Node;
      if (
        popoverRef.current?.contains(node) ||
        inputRef.current?.contains(node)
      ) {
        return;
      }
      setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const pick = useCallback(
    (code: string) => {
      onChange(code);
      setOpen(false);
    },
    [onChange],
  );

  return (
    <div className="relative">
      <div className="relative flex items-center">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={onBlur}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              setHighlight((h) => Math.min(h + 1, filtered.length - 1));
              setOpen(true);
              e.preventDefault();
            } else if (e.key === "ArrowUp") {
              setHighlight((h) => Math.max(h - 1, 0));
              e.preventDefault();
            } else if (e.key === "Enter") {
              const opt = filtered[highlight];
              if (opt) {
                pick(opt.code);
                e.preventDefault();
              }
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={t("s1_okved_placeholder")}
          aria-invalid={invalid || undefined}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listboxId}
          className={cn(
            "h-10 w-full rounded-[9px] border bg-[var(--surface)] pr-[34px] pl-3 font-mono text-[14px] text-[var(--ink-1)] outline-none transition-colors placeholder:font-sans placeholder:text-[var(--ink-4)]",
            "border-[var(--border-strong)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]",
            invalid &&
              "border-[var(--state-bad-fg)] focus:border-[var(--state-bad-fg)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
          )}
        />
        <ChevronDown className="pointer-events-none absolute right-[10px] size-4 text-[var(--ink-3)]" />
      </div>
      {open ? (
        <div
          ref={popoverRef}
          id={listboxId}
          role="listbox"
          className="absolute top-[calc(100%+6px)] left-0 right-0 z-30 max-h-[260px] overflow-y-auto rounded-[10px] border border-[var(--border-strong)] bg-[var(--surface)] shadow-[0_14px_36px_-12px_rgba(14,21,37,0.18)]"
        >
          {catalogQuery.isPending ? (
            <div className="flex items-center gap-2 px-3 py-2 text-[12.5px] text-[var(--ink-4)]">
              <Loader2 className="size-3.5 animate-spin" />
              {t("s1_okved_loading")}
            </div>
          ) : filtered.length === 0 ? (
            <div className="px-3 py-2 text-[12.5px] text-[var(--ink-4)]">
              {t("s1_okved_empty")}
            </div>
          ) : (
            filtered.map((opt, idx) => (
              <button
                key={opt.code}
                type="button"
                role="option"
                aria-selected={idx === highlight}
                onMouseDown={(e) => {
                  e.preventDefault(); // не теряем focus с input до клика
                  pick(opt.code);
                }}
                onMouseEnter={() => setHighlight(idx)}
                className={cn(
                  "grid w-full grid-cols-[60px_1fr] items-baseline gap-[10px] px-3 py-2 text-left text-[13px]",
                  idx === highlight
                    ? "bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]"
                    : "text-[var(--ink-2)]",
                )}
              >
                <span className="font-mono font-semibold">{opt.code}</span>
                <span
                  className={cn(
                    "text-[12.5px]",
                    idx === highlight
                      ? "text-[var(--brand-primary-ink)] opacity-85"
                      : "text-[var(--ink-3)]",
                  )}
                >
                  {labelFor(opt)}
                </span>
              </button>
            ))
          )}
          <div className="border-t border-dashed border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-[11.5px] text-[var(--ink-4)]">
            {t("s1_okved_kbd_hint")}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// ADR-0024 Session 3: ОКЭД owner-initiated toggle
// ─────────────────────────────────────────────────────────────────

export function OkedChangedByOwnerBlock({
  date,
  control,
}: {
  date: string;
  control: Control<FormValues>;
}) {
  const t = useTranslations("accountant.manual_input");
  // Форматирование ISO `yyyy-MM-dd` → `DD.MM.YYYY` для display.
  // Без локалей — banker-style RU/UZ единый формат.
  const formatted = useMemo(() => {
    const d = parse(date, "yyyy-MM-dd", new Date());
    if (!isValid(d)) return date;
    return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
  }, [date]);

  return (
    <div className="mt-2 rounded-[8px] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[12px] text-[var(--ink-3)]">
          <span className="font-semibold text-[var(--ink-2)]">
            {t("s1_oked_changed_label")}:
          </span>{" "}
          <span className="font-mono tabular-nums text-[var(--ink-1)]">
            {formatted}
          </span>
        </div>
        <Controller
          control={control}
          name="step1.okedChangedByOwner"
          render={({ field }) => (
            <label className="flex cursor-pointer items-center gap-2 text-[12px] font-semibold text-[var(--ink-2)]">
              <input
                type="checkbox"
                checked={field.value}
                onChange={(e) => field.onChange(e.target.checked)}
                className="size-[15px] cursor-pointer accent-[var(--brand-primary)]"
                aria-label={t("s1_oked_changed_by_owner_label")}
              />
              {t("s1_oked_changed_by_owner_label")}
            </label>
          )}
        />
      </div>
      <p className="mt-1.5 text-[11.5px] leading-[1.4] text-[var(--ink-4)]">
        {t("s1_oked_changed_help")}
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// CA-039 director-warning block
// ─────────────────────────────────────────────────────────────────

function DirectorRecentWarning() {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      role="note"
      className="mt-2 grid grid-cols-[28px_1fr] items-start gap-2.5 rounded-r-[9px] border-l-[3px] border-[var(--state-warn-fg)] bg-[var(--state-warn-bg)] px-3 py-2.5"
    >
      <div className="grid size-[26px] place-items-center rounded-[7px] bg-[var(--surface)]/60 text-[var(--state-warn-fg)]">
        <TriangleAlert className="size-[14px]" />
      </div>
      <div>
        <div className="text-[12.5px] font-bold text-[var(--state-warn-fg)]">
          {t("s1_recent_director_title")}
        </div>
        <div className="mt-0.5 text-[12px] leading-[1.4] text-[var(--state-warn-fg)] opacity-90">
          {t("s1_recent_director_body")}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────

// CA-039: «свежее» назначение директора (<90 дней) — pre-warning о будущем
// risk-сигнале. Чистая функция, экспортируется для unit-теста.
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

function parseIsoSafe(value: string | undefined): Date | null {
  if (!value) return null;
  const d = parse(value, "yyyy-MM-dd", new Date());
  return isValid(d) ? d : null;
}

function formatBusinessAgeHint(
  value: string | undefined,
  prefix: string,
): string | undefined {
  const age = formatBusinessAge(value);
  return age ? `${prefix}: ${age}` : undefined;
}

function countFilled(s: FormValues["step1"] | undefined): number {
  if (!s) return 0;
  let n = 0;
  if (/^\d{9}$/.test(s.inn ?? "")) n++;
  if ((s.name ?? "").trim().length >= 2) n++;
  if (s.legalForm) n++;
  if (s.registrationDate) n++;
  if ((s.okvedMain ?? "").trim().length >= 2) n++;
  if ((s.directorName ?? "").trim().length >= 2) n++;
  if (s.directorAppointedAt) n++;
  const addr = s.registeredAddress ?? "";
  if (addr.trim().length >= 15 && /\d/.test(addr)) n++;
  return n;
}
