"use client";

import { Bell, ChevronRight, HelpCircle, Search } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

export type Crumb = { label: string; href?: string; current?: boolean };

export function GlobalTopbar({
  crumbs,
  onSearchOpen,
}: {
  crumbs: Crumb[];
  onSearchOpen?: () => void;
}) {
  useEffect(() => {
    if (!onSearchOpen) return;
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onSearchOpen!();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onSearchOpen]);

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-6">
      <nav
        aria-label="Хлебные крошки"
        className="flex min-w-0 items-center gap-1.5 text-[13px]"
      >
        {crumbs.map((c, i) => (
          <span key={i} className="flex min-w-0 items-center gap-1.5">
            {i > 0 && (
              <ChevronRight
                className="size-3.5 text-[var(--ink-4)]"
                aria-hidden
              />
            )}
            {c.href && !c.current ? (
              <Link
                href={c.href}
                className="truncate text-[var(--ink-3)] hover:text-[var(--ink-1)]"
              >
                {c.label}
              </Link>
            ) : (
              <span
                className={
                  c.current
                    ? "truncate font-medium text-[var(--ink-1)]"
                    : "truncate text-[var(--ink-3)]"
                }
              >
                {c.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          onClick={onSearchOpen}
          className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-[12.5px] text-[var(--ink-3)] hover:border-[var(--border-strong)]"
        >
          <Search className="size-3.5" />
          <span>Поиск</span>
          <kbd className="ml-2 rounded border border-[var(--border)] bg-[var(--surface)] px-1.5 py-px font-mono text-[10px] text-[var(--ink-4)]">
            ⌘K
          </kbd>
        </button>
        <Link
          href="/help"
          aria-label="Помощь"
          className="grid size-9 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <HelpCircle className="size-4" />
        </Link>
        <button
          type="button"
          aria-label="Уведомления"
          className="grid size-9 place-items-center rounded-md text-[var(--ink-3)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <Bell className="size-4" />
        </button>
      </div>
    </header>
  );
}
