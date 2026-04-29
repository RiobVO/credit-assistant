import { SearchView } from "./_components/search-view";

export const metadata = { title: "Поиск компании — Uzbekbank Credit" };

export default function BankSearchPage() {
  return (
    <div className="mx-auto w-full max-w-[880px] px-8 pt-8 pb-14">
      <SearchView />
    </div>
  );
}
