import { FolderOpen, IdCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const STATUS_LABEL: Record<string, string> = {
  in_review: "В работе",
  approved: "Одобрено",
  rejected: "Отказ",
  draft: "Черновик",
};

const STATUS_TONE: Record<string, string> = {
  in_review: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--ub-warn-fg)]",
  approved: "border-[#BFE2D2] bg-[var(--ub-ok-bg)] text-[var(--ub-ok-fg)]",
  rejected: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--ub-bad-fg)]",
  draft: "border-[var(--ub-hairline)] bg-[#FAFBFC] text-[var(--ub-ink-3)]",
};

export function SubHeader({
  applicationId,
  borrowerName,
  status,
  documentsCount,
}: {
  applicationId: string;
  borrowerName: string;
  status: string;
  // CA-059: null = endpoint ещё не подключён, кнопка скрывается;
  // 0 = подключён, документов нет — тоже скрываем (нечего открывать).
  documentsCount: number | null;
}) {
  const hasDocuments = documentsCount !== null && documentsCount > 0;
  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2">
      <Badge
        variant="outline"
        className="font-mono text-[11px] tracking-[0.4px] uppercase"
      >
        Заявка {applicationId}
      </Badge>

      <h1 className="m-0 text-[26px] font-semibold tracking-[-0.4px] text-[var(--ub-ink)]">
        {borrowerName}
      </h1>

      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-semibold ${STATUS_TONE[status] ?? STATUS_TONE.draft}`}
      >
        <span className="size-1.5 rounded-full bg-current opacity-70" />
        {STATUS_LABEL[status] ?? status}
      </span>

      <div className="ml-auto flex items-center gap-2">
        {hasDocuments ? (
          <SecondaryAction
            icon={<FolderOpen className="size-4" />}
            label={`Документы (${documentsCount})`}
          />
        ) : null}
        <SecondaryAction icon={<IdCard className="size-4" />} label="Карточка клиента" />
      </div>
    </div>
  );
}

function SecondaryAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="inline-flex h-[34px] items-center gap-2 rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-3 text-[12.5px] font-medium text-[var(--ub-ink-2)] transition-colors hover:bg-[#FAFBFC]"
    >
      {icon}
      {label}
    </button>
  );
}
