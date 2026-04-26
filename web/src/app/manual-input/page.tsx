// CA-018: shared manual-input route. Переехал из `(accountant)/manual-input`
// в root — одна URL `/manual-input` обслуживает оба режима, mode-aware chrome
// решается в AppShell (`app/manual-input/layout.tsx`).
//
// Симметрично 4.G для `/dossier/[id]`.

import { ManualInputView } from "@/features/manual-input/manual-input-view";

export default function ManualInputPage() {
  return <ManualInputView />;
}
