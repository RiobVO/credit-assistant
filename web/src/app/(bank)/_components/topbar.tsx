"use client";

import { Bell, ChevronRight, HelpCircle } from "lucide-react";
import { usePathname } from "next/navigation";

const TITLE_MAP: Array<{ pattern: RegExp; title: string }> = [
  { pattern: /^\/search(\/|$)/, title: "Поиск компании" },
  { pattern: /^\/history(\/|$)/, title: "История проверок" },
  { pattern: /^\/dossier(\/|$)/, title: "Кредитное досье" },
  { pattern: /^\/manual-input(\/|$)/, title: "Новая заявка" },
  { pattern: /^\/settings(\/|$)/, title: "Настройки" },
  { pattern: /^\/help(\/|$)/, title: "Помощь" },
];

function titleFor(pathname: string): string {
  const hit = TITLE_MAP.find((m) => m.pattern.test(pathname));
  return hit ? hit.title : "Bank Mode";
}

export function BankTopbar() {
  const pathname = usePathname();
  const title = titleFor(pathname);

  return (
    <header className="sticky top-0 z-10 flex h-[60px] items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-8">
      <nav aria-label="Хлебные крошки" className="flex items-center gap-2">
        <span className="text-[14px] text-[var(--ink-3)]">Bank Mode</span>
        <ChevronRight className="size-3.5 text-[var(--ink-4)]" aria-hidden />
        <span className="text-[15px] font-semibold tracking-[-0.01em] text-[var(--ink-1)]">
          {title}
        </span>
      </nav>

      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label="Уведомления"
          title="Уведомления"
          className="grid size-9 place-items-center rounded-md text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <Bell className="size-4" />
        </button>
        <a
          href="/help"
          className="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-[13px] font-medium text-[var(--ink-1)] transition-colors hover:bg-[var(--surface-2)]"
        >
          <HelpCircle className="size-3.5" />
          Справка
        </a>
      </div>
    </header>
  );
}
