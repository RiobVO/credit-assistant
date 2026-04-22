import { SearchForm } from "./_components/search-form";

export const metadata = { title: "Поиск заёмщика — Uzbekbank Credit" };

export default function BankSearchPage() {
  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-1 flex-col px-8 py-10">
      <header className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-[-0.2px] text-[var(--ca-text-strong)]">
          Поиск заёмщика
        </h1>
        <p className="mt-1 text-[13px] text-[var(--ca-text-muted)]">
          Введите ИНН — система найдёт существующее досье или предложит загрузить выгрузки.
        </p>
      </header>

      <SearchForm />
    </div>
  );
}
