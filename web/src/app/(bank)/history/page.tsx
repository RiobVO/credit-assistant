import { HistoryView } from "./_components/history-view";

export const metadata = { title: "История досье — Uzbekbank Credit" };

export default function BankHistoryPage() {
  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col px-8 py-10">
      <header className="mb-6">
        <h1 className="text-[22px] font-semibold tracking-[-0.2px] text-[var(--ca-text-strong)]">
          История досье
        </h1>
        <p className="mt-1 text-[13px] text-[var(--ca-text-muted)]">
          Все досье, созданные в Bank Mode. Фильтр «Мои» / «Все» и поиск по ИНН/имени.
        </p>
      </header>

      <HistoryView />
    </div>
  );
}
