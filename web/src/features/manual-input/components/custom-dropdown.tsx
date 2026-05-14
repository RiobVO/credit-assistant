"use client";

// Custom-dropdown (popover-listbox поверх <button>) для случаев, где native
// <select> расходится с design tokens / focus-ring tone. Extracted из
// soliq-upload в Phase 8 для переиспользования в Step 3 (срок кредита).
//
// `label` опциональный: когда компонент рендерится внутри <Field>, label
// ставит обёртка → передавать `label` не нужно (иначе будет дублироваться).
//
// TODO[CA-DS22]: keyboard nav (↑↓ Enter Esc). Сейчас только mouse-click +
// outside-click close. Phase 6 OkvedAutocomplete делал нав через ↑↓ —
// extract в shared <Listbox> primitive когда понадобится третий consumer.

import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

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
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const current = options.find((o) => o.value === value);
  const triggerTop = label ? "top-[68px]" : "top-[48px]";

  return (
    <div ref={rootRef} className="relative flex flex-col gap-1.5">
      {label ? (
        <label className="text-[12.5px] font-medium text-[var(--ink-2)]">
          {label}
        </label>
      ) : null}
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
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
          role="listbox"
          className={cn(
            "absolute right-0 left-0 z-20 max-h-[240px] overflow-y-auto rounded-[10px] border border-[var(--border-strong)] bg-[var(--surface)] shadow-[0_14px_36px_-12px_rgba(14,21,37,0.18)]",
            triggerTop,
          )}
        >
          {options.map((opt) => {
            const selected = opt.value === value;
            return (
              <li
                key={String(opt.value)}
                role="option"
                aria-selected={selected}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex cursor-pointer items-center justify-between px-3 py-2 text-[13.5px] transition-colors",
                  selected
                    ? "bg-[var(--brand-primary-soft)] font-semibold text-[var(--brand-primary-ink)]"
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
