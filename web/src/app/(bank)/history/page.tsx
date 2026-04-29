import { BankPageContainer } from "../_components/page-container";

import { HistoryView } from "./_components/history-view";

export const metadata = { title: "История проверок — Uzbekbank Credit" };

export default function BankHistoryPage() {
  return (
    <BankPageContainer>
      <HistoryView />
    </BankPageContainer>
  );
}
