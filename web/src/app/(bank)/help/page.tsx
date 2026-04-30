import { BankPageContainer } from "../_components/page-container";

import { HelpView } from "./_components/help-view";

export const metadata = { title: "Помощь — Uzbekbank Credit" };

export default function BankHelpPage() {
  return (
    <BankPageContainer>
      <HelpView />
    </BankPageContainer>
  );
}
