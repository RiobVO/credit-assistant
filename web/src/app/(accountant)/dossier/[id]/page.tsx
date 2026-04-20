import { DossierView } from "./_components/dossier-view";

// Server-компонент тонкий: распаковывает `params` (Next 15 App Router
// возвращает Promise) и передаёт в клиентскую обёртку. Реальная загрузка
// и рендер — внутри DossierView через TanStack Query.
export default async function DossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <DossierView dossierId={id} />;
}
