// Скелетон-вью на время загрузки досье. Повторяет layout страницы
// с серыми блоками + animate-pulse — глаз ловит будущее место контента.

import { Topbar } from "@/components/topbar";

import { APP_MODE } from "@/lib/config";

const PREFIX =
  APP_MODE === "bank"
    ? [{ label: "История" }, { label: "Досье" }]
    : [{ label: "Заявки" }, { label: "Досье" }];

export function DossierSkeleton() {
  return (
    <>
      <Topbar crumbs={[...PREFIX, { label: "—", current: true }]} />
      <div className="w-full max-w-[1280px] px-8 pt-7 pb-12">
        <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2">
          <Block className="h-5 w-28" />
          <Block className="h-7 w-72" />
          <Block className="h-7 w-24 rounded-full" />
          <div className="ml-auto flex items-center gap-2">
            <Block className="h-[34px] w-32 rounded-md" />
            <Block className="h-[34px] w-40 rounded-md" />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <Card className="h-[260px]" />
          <Card className="h-[260px]" />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Card className="h-[120px]" />
          <Card className="h-[120px]" />
          <Card className="h-[120px]" />
          <Card className="h-[120px]" />
        </div>

        <div className="mt-4">
          <Card className="h-[330px]" />
        </div>

        <div className="mt-4">
          <Card className="h-[200px]" />
        </div>
      </div>
    </>
  );
}

function Card({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)] ${className}`}
    />
  );
}

function Block({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-[#E4E7EC] ${className}`}
      aria-hidden="true"
    />
  );
}
