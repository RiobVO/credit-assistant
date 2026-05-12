"use client";

import { Search, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

type Item = { labelKey: string; href: string; sectionKey: "section_navigation" | "section_actions" };

const ITEMS: Item[] = [
  { labelKey: "search_borrower", href: "/search", sectionKey: "section_navigation" },
  { labelKey: "history", href: "/history", sectionKey: "section_navigation" },
  { labelKey: "new_application", href: "/manual-input", sectionKey: "section_actions" },
  { labelKey: "settings", href: "/settings", sectionKey: "section_navigation" },
  { labelKey: "help", href: "/help", sectionKey: "section_navigation" },
];

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const t = useTranslations("shared.palette");
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      // eslint-disable-next-line react-hooks/set-state-in-effect -- сброс query при открытии palette; нельзя выразить через initial state
      setQuery("");
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Локализованные items пересоздаются при смене query — t() в нескольких местах ниже.
  const itemsLocalized = useMemo(
    () =>
      ITEMS.map((i) => ({
        ...i,
        label: t(i.labelKey as "search_borrower"),
        section: t(i.sectionKey),
      })),
    [t],
  );

  if (!open) return null;

  const filtered = itemsLocalized.filter((i) =>
    i.label.toLowerCase().includes(query.toLowerCase()),
  );
  const grouped = filtered.reduce<Record<string, (typeof itemsLocalized)[number][]>>((acc, item) => {
    (acc[item.section] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start pt-[10vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Командная палитра"
    >
      <button
        type="button"
        aria-label={t("close_aria")}
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />
      <div className="relative z-10 mx-auto w-full max-w-[600px] rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-xl">
        <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3">
          <Search className="size-4 text-[var(--ink-4)]" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("placeholder")}
            className="flex-1 bg-transparent text-[14px] text-[var(--ink-1)] placeholder-[var(--ink-4)] focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label={t("close_aria")}
            className="text-[var(--ink-4)] hover:text-[var(--ink-1)]"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="max-h-[400px] overflow-y-auto p-2">
          {Object.entries(grouped).length === 0 ? (
            <div className="px-3 py-6 text-center text-[13px] text-[var(--ink-3)]">
              {t("empty")}
            </div>
          ) : (
            Object.entries(grouped).map(([section, items]) => (
              <div key={section} className="mb-2">
                <div className="px-2 pb-1 text-[10.5px] font-semibold tracking-[0.1em] text-[var(--ink-4)] uppercase">
                  {section}
                </div>
                {items.map((item) => (
                  <button
                    key={item.href}
                    type="button"
                    onClick={() => {
                      router.push(item.href);
                      onClose();
                    }}
                    className="block w-full rounded-md px-3 py-2 text-left text-[13.5px] text-[var(--ink-1)] hover:bg-[var(--surface-2)]"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
