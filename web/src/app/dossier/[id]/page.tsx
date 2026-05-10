// Shared dossier page: переехал из `(accountant)/dossier/[id]` в root —
// одна URL `/dossier/[id]` обслуживает оба режима, mode-aware chrome
// решается в AppShell (`app/dossier/[id]/layout.tsx`).

import { DossierView } from "@/features/dossier/dossier-view";

export default async function DossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DossierView dossierId={id} />;
}
