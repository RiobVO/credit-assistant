import { BankPageContainer } from "../_components/page-container";

import { SettingsView } from "./_components/settings-view";

export const metadata = { title: "Настройки — Uzbekbank Credit" };

export default function BankSettingsPage() {
  return (
    <BankPageContainer>
      <SettingsView />
    </BankPageContainer>
  );
}
