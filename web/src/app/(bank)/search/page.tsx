// Placeholder — Phase 4.F наполнит этот экран реальным гибридным поиском.

import { Search } from "lucide-react";

export const metadata = { title: "Поиск заёмщика — Uzbekbank Credit" };

export default function BankSearchPage() {
  return (
    <div className="flex flex-1 flex-col px-8 py-10">
      <header className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-[-0.2px] text-[var(--ca-text-strong)]">
          Поиск заёмщика
        </h1>
        <p className="mt-1 text-[13px] text-[var(--ca-text-muted)]">
          Введите ИНН — система найдёт существующее досье или предложит создать новое.
        </p>
      </header>

      <div className="max-w-[640px] rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3 rounded-md border border-[var(--ca-line)] bg-[var(--ca-bg-soft)] px-4 py-3 text-[13.5px] text-[var(--ca-text-muted)]">
          <Search className="size-4 text-[var(--ca-text-muted)]" />
          <span>Поле поиска по ИНН — будет включено в Phase 4.F</span>
        </div>
        <p className="mt-4 text-[12.5px] text-[var(--ca-text-muted)]">
          Авторизация и аудит уже включены: запросы фиксируются в журнале
          под учётной записью текущего аналитика.
        </p>
      </div>
    </div>
  );
}
