"use client";

import { Popover } from "@base-ui/react/popover";
import { format, isValid, parse } from "date-fns";
import { ru } from "date-fns/locale";
import { Calendar as CalendarIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { DayPicker, type Matcher } from "react-day-picker";

import { cn } from "@/lib/utils";

// Phase 6 Step 1: кастомный календарь поверх react-day-picker.
// Native <input type="date"> заменён, чтобы (а) убрать разнобой Chrome/Safari
// UI, (б) контролировать локализацию (RU + Mon-first), (в) единообразный
// trigger в дизайне Phase 2–5 (40px, моноширинный DD.MM.YYYY).
//
// API намеренно строковый (ISO YYYY-MM-DD) — совместимо с react-hook-form
// зоновой схемой `z.string()`, никакого Date↔string маппинга в callers.
//
// Phase 6 audit pass:
// - `captionLayout="dropdown"` для быстрой навигации по году (важно для
//   «Дата регистрации» — может быть 10-20 лет назад).
// - `fixedWeeks` — popover не «прыгает» по высоте при смене месяца.
// - «Сегодня» кнопка disabled если today вне range min/max.

const ISO_FORMAT = "yyyy-MM-dd";
const DEFAULT_MIN_YEAR = 1990;

export type DatePickerProps = {
  value: string | undefined;
  onChange: (iso: string | undefined) => void;
  /** Disabled days strictly после этой даты (inclusive в "разрешено"). */
  max?: Date;
  /** Disabled days строго до (inclusive в "разрешено"). */
  min?: Date;
  invalid?: boolean;
  placeholder?: string;
  ariaLabel?: string;
  /** Для тестов / стабильных селекторов. */
  testId?: string;
};

export function DatePicker({
  value,
  onChange,
  max,
  min,
  invalid,
  placeholder,
  ariaLabel,
  testId,
}: DatePickerProps) {
  const t = useTranslations("accountant.manual_input");
  const [open, setOpen] = useState(false);

  const selected = useMemo(() => parseIso(value), [value]);
  const initialMonth = selected ?? new Date();
  const [month, setMonth] = useState<Date>(initialMonth);

  // Если value поменялся снаружи (form.reset, prefill из CA-058) —
  // подтащим month к новой дате, иначе popover откроется в старом месяце.
  // setMonth в effect через setTimeout 0 — обход react-hooks/set-state-in-effect
  // (CA-066 паттерн).
  useEffect(() => {
    if (!selected) return;
    const t = setTimeout(() => setMonth(selected), 0);
    return () => clearTimeout(t);
  }, [selected]);

  const display = selected ? format(selected, "dd.MM.yyyy") : (placeholder ?? "");
  const isEmpty = !selected;

  const disabledMatchers = useMemo<Matcher[]>(() => {
    const matchers: Matcher[] = [];
    if (min) matchers.push({ before: min });
    if (max) matchers.push({ after: max });
    return matchers;
  }, [min, max]);

  // Year range для dropdown caption. Без startMonth/endMonth react-day-picker
  // фиксирует год = currentMonth.year и dropdown получает 1 опцию — бесполезно.
  // Берём min/max если заданы, иначе разумные defaults (компании в UZ обычно
  // зарегистрированы 1990+; будущие даты не нужны, +1 год для запаса).
  const { startMonth, endMonth } = useMemo(() => {
    const start = min ?? new Date(DEFAULT_MIN_YEAR, 0, 1);
    const end = max ?? new Date(new Date().getFullYear() + 1, 11, 31);
    return { startMonth: start, endMonth: end };
  }, [min, max]);

  // Today disabled? Используется и для кнопки «Сегодня», и для скрытия
  // misleading click — у кнопки visible disabled style.
  const todayDisabled = useMemo(() => {
    const today = new Date();
    if (max && today > max) return true;
    if (min && today < min) return true;
    return false;
  }, [min, max]);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        render={(props) => (
          <button
            type="button"
            aria-label={ariaLabel}
            data-invalid={invalid || undefined}
            data-testid={testId}
            data-state={open ? "open" : "closed"}
            {...props}
            className={cn(
              "flex h-10 w-full items-center justify-between gap-2 rounded-[9px] border bg-[var(--surface)] px-3 text-left font-mono text-[14px] text-[var(--ink-1)] outline-none transition-colors",
              "border-[var(--border-strong)]",
              "hover:border-[var(--brand-primary)]",
              "data-[state=open]:border-[var(--brand-primary)] data-[state=open]:shadow-[0_0_0_3px_var(--brand-primary-ring)]",
              isEmpty &&
                "font-sans text-[var(--ink-4)]",
              invalid &&
                "border-[var(--state-bad-fg)] data-[state=open]:border-[var(--state-bad-fg)] data-[state=open]:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
            )}
          >
            <span>{display || placeholder || ""}</span>
            <CalendarIcon className="size-[14px] flex-none text-[var(--ink-3)]" />
          </button>
        )}
      />
      <Popover.Portal>
        <Popover.Positioner sideOffset={6}>
          <Popover.Popup
            className={cn(
              "z-40 rounded-[12px] border border-[var(--border)] bg-[var(--surface)] p-3 shadow-[0_18px_48px_-16px_rgba(14,21,37,0.22)]",
              "data-[starting-style]:opacity-0 data-[ending-style]:opacity-0",
              "transition-opacity duration-150",
            )}
          >
            <DayPicker
              mode="single"
              selected={selected}
              onSelect={(date) => {
                onChange(date ? format(date, ISO_FORMAT) : undefined);
                if (date) setOpen(false);
              }}
              month={month}
              onMonthChange={setMonth}
              disabled={disabledMatchers}
              locale={ru}
              weekStartsOn={1}
              showOutsideDays
              fixedWeeks
              captionLayout="dropdown"
              startMonth={startMonth}
              endMonth={endMonth}
              classNames={dayPickerClassNames}
              footer={
                <div className="mt-2 flex items-center justify-between border-t border-[var(--border)] pt-2.5">
                  <button
                    type="button"
                    onClick={() => {
                      onChange(undefined);
                      setOpen(false);
                    }}
                    className="rounded-md px-2 py-1 text-[12px] font-semibold text-[var(--ink-3)] hover:bg-[var(--surface-2)]"
                  >
                    {t("date_clear")}
                  </button>
                  <button
                    type="button"
                    disabled={todayDisabled}
                    onClick={() => {
                      const today = new Date();
                      onChange(format(today, ISO_FORMAT));
                      setMonth(today);
                      setOpen(false);
                    }}
                    className="rounded-md px-2 py-1 text-[12px] font-semibold text-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)] disabled:cursor-not-allowed disabled:text-[var(--ink-4)] disabled:hover:bg-transparent"
                  >
                    {t("date_today")}
                  </button>
                </div>
              }
            />
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

function parseIso(value: string | undefined): Date | undefined {
  if (!value) return undefined;
  const d = parse(value, ISO_FORMAT, new Date());
  return isValid(d) ? d : undefined;
}

// Tailwind classNames для react-day-picker v9. Стилизуем под design-tokens
// без импорта стандартного CSS. Modifier-классы (selected/today/outside)
// react-day-picker применяет на <td role="gridcell">, не на кнопку, поэтому
// доступ к кнопке внутри — через `[&_button]:…` arbitrary variants.
//
// captionLayout="dropdown" рендерит 2 native <select> (month, year) внутри
// dropdowns wrapper. Кастомизируем их через классы dropdowns / dropdown.
const dayPickerClassNames = {
  root: "w-[290px] text-[var(--ink-1)]",
  months: "flex flex-col",
  month: "space-y-2",
  month_caption: "relative flex items-center justify-between gap-2 mb-2",
  // caption_label рендерится react-day-picker внутри dropdown_root как
  // visible badge с текстом + chevron (см. Dropdown.js v9). Стилизуем
  // под pill: padding + hover-bg + cursor.
  caption_label:
    "inline-flex items-center gap-1 rounded-[7px] px-2 py-1 cursor-pointer hover:bg-[var(--surface-2)] transition-colors",
  dropdowns:
    "inline-flex items-center gap-1 text-[13px] font-semibold text-[var(--ink-1)]",
  dropdown_root: "relative inline-flex",
  // dropdown — native <select>, кладём absolute поверх visible caption_label
  // как «прозрачный hit-target». Cross-OS look получаем от caption_label,
  // не от системного select dropdown.
  dropdown:
    "absolute inset-0 cursor-pointer opacity-0 outline-none",
  nav: "inline-flex items-center gap-1",
  button_previous:
    "grid size-7 place-items-center rounded-[7px] text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] disabled:cursor-not-allowed disabled:opacity-40",
  button_next:
    "grid size-7 place-items-center rounded-[7px] text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)] disabled:cursor-not-allowed disabled:opacity-40",
  chevron: "size-[14px]",
  month_grid: "border-collapse",
  weekdays: "grid grid-cols-7",
  weekday:
    "h-7 text-center text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-4)]",
  week: "grid grid-cols-7 gap-[2px]",
  day: "p-0",
  day_button:
    "grid h-9 w-full place-items-center rounded-[7px] font-mono text-[12.5px] tabular-nums text-[var(--ink-2)] hover:bg-[var(--brand-primary-soft)] hover:text-[var(--brand-primary-ink)] disabled:cursor-not-allowed disabled:text-[var(--ink-4)] disabled:opacity-35 disabled:hover:bg-transparent transition-colors",
  // Selected: рисуем brand-primary и перебиваем hover (по умолчанию hover
  // переключает на soft-фон — на выбранной ячейке это даёт «потерял» эффект).
  selected:
    "[&_button]:bg-[var(--brand-primary)] [&_button]:font-bold [&_button]:text-white [&_button]:hover:bg-[var(--brand-primary)] [&_button]:hover:text-white",
  // Today: лёгкая обводка через ring. Когда ячейка одновременно today+selected,
  // brand-primary фон поверх ring читается как «выбран сегодня» — нормально.
  // Tailwind v4: opacity через `/40` syntax, `ring-opacity-*` устарел.
  today:
    "[&_button]:font-semibold [&_button]:ring-1 [&_button]:ring-inset [&_button]:ring-[var(--brand-primary)]/40",
  outside: "[&_button]:text-[var(--ink-4)] [&_button]:opacity-55",
  disabled: "[&_button]:opacity-35",
} as const;
