import { SearchView } from "./_components/search-view";

export const metadata = { title: "Поиск компании — Uzbekbank Credit" };

export default function BankSearchPage() {
  // Phase 2 DS-PHASE-2: container 980px (preview-параметры). max-w для focused
  // hero, padding bottom 80px чтобы result-card не упирался в floor.
  return (
    <div className="relative mx-auto w-full max-w-[980px] px-12 pt-10 pb-20">
      <SearchView />
    </div>
  );
}
