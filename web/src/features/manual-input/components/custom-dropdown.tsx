"use client";

// Custom-dropdown (popover-listbox поверх <button>) для случаев, где native
// <select> расходится с design tokens / focus-ring tone. Extracted из
// soliq-upload в Phase 8 для переиспользования в Step 3 (срок кредита).
//
// `label` опциональный: когда компонент рендерится внутри <Field>, label
// ставит обёртка → передавать `label` не нужно (иначе будет дублироваться).
//
// CA-DS22: full keyboard nav. ArrowDown/Up двигают highlight (clamp к
// границам), Home/End → первая/последняя, Enter commit'ит highlighted,
// Escape закрывает без выбора. На open initial highlight = индекс
// currently-selected value (не 0) — пользователь приходит туда, где он есть.
// aria-activedescendant на button ссылается на id active option.

import { ChevronDown } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export type DropdownOption<T> = { value: T; label: string };

export function CustomDropdown<T extends string | number>({
  label,
  value,
  onChange,
  options,
}: {
  label?: string;
  value: T;
  onChange: (next: T) => void;
  options: DropdownOption<T>[];
}) {
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const optionIdPrefix = useId();

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // На каждое open ставим highlight на currently-selected option (или 0,
  // если value не нашёлся — например initial undefined). Когда юзер закрыл
  // и открыл снова, начинаем с актуального value, не с stale highlight.
  // ESLint react-hooks/set-state-in-effect запрещает синхронный setState
  // в effect body — обходим через macrotask (setTimeout 0), pattern из
  // OkvedAutocomplete / InnInput.
  useEffect(() => {
    if (!open) return;
    const idx = options.findIndex((o) => o.value === value);
    const t = setTimeout(() => setHighlight(idx >= 0 ? idx : 0), 0);
    return () => clearTimeout(t);
  }, [open, options, value]);

  const current = options.find((o) => o.value === value);
  const triggerTop = label ? "top-[68px]" : "top-[48px]";

  const optionId = useMemo(
    () => (idx: number) => `${optionIdPrefix}-opt-${idx}`,
    [optionIdPrefix],
  );

  function commit(idx: number) {
    const opt = options[idx];
    if (!opt) return;
    onChange(opt.value);
    setOpen(false);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (!open) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(true);
        return;
      }
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlight((h) => Math.min(h + 1, options.length - 1));
        return;
      case "ArrowUp":
        e.preventDefault();
        setHighlight((h) => Math.max(h - 1, 0));
        return;
      case "Home":
        e.preventDefault();
        setHighlight(0);
        return;
      case "End":
        e.preventDefault();
        setHighlight(options.length - 1);
        return;
      case "Enter":
      case " ":
        e.preventDefault();
        commit(highlight);
        return;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        return;
    }
  }

  return (
    <div ref={rootRef} className="relative flex flex-col gap-1.5">
      {label ? (
        <label className="text-[12.5px] font-medium text-[var(--ink-2)]">
          {label}
        </label>
      ) : null}
      <button
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        aria-activedescendant={open ? optionId(highlight) : undefined}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={handleKeyDown}
        className="flex h-[40px] items-center justify-between gap-2 rounded-[9px] border border-[var(--border-strong)] bg-[var(--surface)] px-3 text-left text-[14px] text-[var(--ink-1)] transition-colors hover:border-[var(--brand-primary)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)] focus:outline-none"
      >
        <span>{current?.label ?? "—"}</span>
        <ChevronDown
          className={cn(
            "size-[14px] flex-none text-[var(--ink-3)] transition-transform duration-150",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          className={cn(
            "absolute right-0 left-0 z-20 max-h-[240px] overflow-y-auto rounded-[10px] border border-[var(--border-strong)] bg-[var(--surface)] shadow-[0_14px_36px_-12px_rgba(14,21,37,0.18)]",
            triggerTop,
          )}
        >
          {options.map((opt, idx) => {
            const selected = opt.value === value;
            const highlighted = idx === highlight;
            return (
              <li
                key={String(opt.value)}
                id={optionId(idx)}
                role="option"
                aria-selected={selected}
                onMouseEnter={() => setHighlight(idx)}
                onClick={() => commit(idx)}
                className={cn(
                  "flex cursor-pointer items-center justify-between px-3 py-2 text-[13.5px] transition-colors",
                  selected
                    ? "bg-[var(--brand-primary-soft)] font-semibold text-[var(--brand-primary-ink)]"
                    : highlighted
                      ? "bg-[var(--surface-2)] text-[var(--ink-1)]"
                      : "text-[var(--ink-2)] hover:bg-[var(--surface-2)]",
                )}
              >
                <span>{opt.label}</span>
                {selected ? <span className="font-bold">✓</span> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
