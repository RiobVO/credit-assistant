"use client";

import { CornerDownLeft, Search, X } from "lucide-react";
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
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      // eslint-disable-next-line react-hooks/set-state-in-effect -- сброс query+activeIndex при открытии palette; нельзя выразить через initial state
      setQuery("");
      setActiveIndex(0);
    }
  }, [open]);

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

  const filtered = useMemo(
    () =>
      itemsLocalized.filter((i) =>
        i.label.toLowerCase().includes(query.toLowerCase()),
      ),
    [itemsLocalized, query],
  );

  // Когда фильтр сужается — активный индекс может выйти за границы, клампим.
  useEffect(() => {
    if (activeIndex >= filtered.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- кламп после сужения filtered
      setActiveIndex(0);
    }
  }, [filtered.length, activeIndex]);

  useEffect(() => {
    if (!open) return;
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (filtered.length === 0 ? 0 : (i + 1) % filtered.length));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) =>
          filtered.length === 0 ? 0 : (i - 1 + filtered.length) % filtered.length,
        );
        return;
      }
      if (e.key === "Enter") {
        const target = filtered[activeIndex];
        if (target) {
          e.preventDefault();
          router.push(target.href);
          onClose();
        }
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose, filtered, activeIndex, router]);

  if (!open) return null;

  // Группировка с сохранением исходного порядка filtered (для стабильного activeIndex).
  const grouped: Array<{ section: string; items: Array<{ item: (typeof filtered)[number]; flatIndex: number }> }> = [];
  filtered.forEach((item, flatIndex) => {
    const last = grouped[grouped.length - 1];
    if (last && last.section === item.section) {
      last.items.push({ item, flatIndex });
    } else {
      grouped.push({ section: item.section, items: [{ item, flatIndex }] });
    }
  });

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start pt-[10vh]"
      role="dialog"
      aria-modal="true"
      aria-label={t("close_aria")}
    >
      <button
        type="button"
        aria-label={t("close_aria")}
        onClick={onClose}
        className="absolute inset-0 bg-[rgb(11,18,32)]/60 backdrop-blur-sm"
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
          {grouped.length === 0 ? (
            <div className="px-3 py-6 text-center text-[13px] text-[var(--ink-3)]">
              {t("empty")}
            </div>
          ) : (
            grouped.map(({ section, items }) => (
              <div key={section} className="mb-2">
                <div className="px-2 pb-1 text-[10.5px] font-semibold tracking-[0.1em] text-[var(--ink-4)] uppercase">
                  {section}
                </div>
                {items.map(({ item, flatIndex }) => {
                  const isActive = flatIndex === activeIndex;
                  return (
                    <button
                      key={item.href}
                      type="button"
                      onMouseMove={() => setActiveIndex(flatIndex)}
                      onClick={() => {
                        router.push(item.href);
                        onClose();
                      }}
                      className={
                        isActive
                          ? "flex w-full items-center justify-between rounded-md bg-[var(--surface-2)] px-3 py-2 text-left text-[13.5px] text-[var(--ink-1)]"
                          : "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-[13.5px] text-[var(--ink-1)]"
                      }
                    >
                      <span>{item.label}</span>
                      {isActive ? (
                        <kbd className="ml-2 inline-flex h-5 items-center gap-1 rounded border border-[var(--border-strong)] bg-[var(--surface)] px-1.5 text-[11px] font-medium text-[var(--ink-3)]">
                          <CornerDownLeft className="size-3" aria-hidden />
                        </kbd>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
