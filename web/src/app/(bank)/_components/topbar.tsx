"use client";

import { Bell, ChevronRight, HelpCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePathname } from "next/navigation";

type TitleKey =
  | "title_search"
  | "title_history"
  | "title_dossier"
  | "title_manual_input"
  | "title_settings"
  | "title_help";

const TITLE_MAP: Array<{ pattern: RegExp; key: TitleKey }> = [
  { pattern: /^\/search(\/|$)/, key: "title_search" },
  { pattern: /^\/history(\/|$)/, key: "title_history" },
  { pattern: /^\/dossier(\/|$)/, key: "title_dossier" },
  { pattern: /^\/manual-input(\/|$)/, key: "title_manual_input" },
  { pattern: /^\/settings(\/|$)/, key: "title_settings" },
  { pattern: /^\/help(\/|$)/, key: "title_help" },
];

export function BankTopbar() {
  const pathname = usePathname();
  const t = useTranslations("bank.topbar");
  const tShared = useTranslations("shared.topbar");
  const hit = TITLE_MAP.find((m) => m.pattern.test(pathname));
  const title = hit ? t(hit.key) : t("title_fallback");

  return (
    <header className="sticky top-0 z-10 flex h-[60px] items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-8">
      <nav aria-label={tShared("breadcrumbs_aria")} className="flex items-center gap-2">
        <span className="text-[14px] text-[var(--ink-3)]">Bank Mode</span>
        <ChevronRight className="size-3.5 text-[var(--ink-4)]" aria-hidden />
        <span className="text-[15px] font-semibold tracking-[-0.01em] text-[var(--ink-1)]">
          {title}
        </span>
      </nav>

      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={tShared("bell_aria")}
          title={tShared("bell_aria")}
          className="grid size-9 place-items-center rounded-md text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]"
        >
          <Bell className="size-4" />
        </button>
        <a
          href="/help"
          className="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-[13px] font-medium text-[var(--ink-1)] transition-colors hover:bg-[var(--surface-2)]"
        >
          <HelpCircle className="size-3.5" />
          {t("help_link")}
        </a>
      </div>
    </header>
  );
}
