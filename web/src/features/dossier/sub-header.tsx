"use client";

import { FolderOpen, IdCard } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";

const STATUS_TONE: Record<string, string> = {
  in_review: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--state-warn-fg)]",
  approved: "border-[#BFE2D2] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
  rejected: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--state-bad-fg)]",
  draft: "border-[var(--border)] bg-[#FAFBFC] text-[var(--ink-3)]",
};

const STATUS_KEY: Record<
  string,
  "status_in_review" | "status_approved" | "status_rejected" | "status_draft"
> = {
  in_review: "status_in_review",
  approved: "status_approved",
  rejected: "status_rejected",
  draft: "status_draft",
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
  const t = useTranslations("dossier.sub_header");
  const hasDocuments = documentsCount !== null && documentsCount > 0;
  const statusKey = STATUS_KEY[status];
  const statusLabel = statusKey ? t(statusKey) : status;
  return (
    <div className="mb-5 flex flex-wrap items-center gap-x-4 gap-y-2">
      <Badge
        variant="outline"
        className="font-mono text-[11px] tracking-[0.4px] uppercase"
      >
        {t("application_label", { id: applicationId })}
      </Badge>

      <h1 className="m-0 text-[26px] font-semibold tracking-[-0.4px] text-[var(--ink-1)]">
        {borrowerName}
      </h1>

      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12px] font-semibold ${STATUS_TONE[status] ?? STATUS_TONE.draft}`}
      >
        <span className="size-1.5 rounded-full bg-current opacity-70" />
        {statusLabel}
      </span>

      <div className="ml-auto flex items-center gap-2">
        {hasDocuments ? (
          <SecondaryAction
            icon={<FolderOpen className="size-4" />}
            label={t("documents_label", { count: documentsCount })}
          />
        ) : null}
        <SecondaryAction
          icon={<IdCard className="size-4" />}
          label={t("client_card")}
        />
      </div>
    </div>
  );
}

function SecondaryAction({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      className="inline-flex h-[34px] items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-[12.5px] font-medium text-[var(--ink-2)] transition-colors hover:bg-[#FAFBFC]"
    >
      {icon}
      {label}
    </button>
  );
}
