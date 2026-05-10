// Placeholder — Phase 4.F наполнит таблицу истории досье.

import { Clock } from "lucide-react";

export const metadata = { title: "История досье — Uzbekbank Credit" };

export default function BankHistoryPage() {
  return (
    <div className="flex flex-1 flex-col px-8 py-10">
      <header className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-[-0.2px] text-[var(--ca-text-strong)]">
          История досье
        </h1>
        <p className="mt-1 text-[13px] text-[var(--ca-text-muted)]">
          Все досье, созданные в Bank Mode. Фильтры «Мои» / «Все» и поиск по ИНН/имени.
        </p>
      </header>

      <div className="rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3 rounded-md border border-[var(--ca-line)] bg-[var(--ca-bg-soft)] px-4 py-6 text-[13.5px] text-[var(--ca-text-muted)]">
          <Clock className="size-4 text-[var(--ca-text-muted)]" />
          <span>Таблица досье — будет включена в Phase 4.F</span>
        </div>
      </div>
    </div>
  );
}
