"use client";

import { CheckCircle2, ShieldAlert, ShieldQuestion, ShieldX } from "lucide-react";
import { useTranslations } from "next-intl";

import { SectionCard } from "@/components/section-card";
import type { DossierViewDto, GnkStatus } from "@/lib/api";

const LEGAL_FORM_KEY: Record<
  DossierViewDto["borrower"]["legal_form"],
  | "legal_llc"
  | "legal_pe"
  | "legal_ltd"
  | "legal_jsc"
  | "legal_ie"
  | "legal_other"
> = {
  llc: "legal_llc",
  pe: "legal_pe",
  ltd: "legal_ltd",
  jsc: "legal_jsc",
  ie: "legal_ie",
  other: "legal_other",
};

// Phase 9 + T0.3.2: SectionCard shell. ГНК pill теперь основан на real-uploaded
// справке (Phase A — manual upload, см. shared/gnk_certificate.py). Если справка
// загружена с status="active" → green check + источник «загружено аналитиком».
// Без справки — нет pill (раньше показывался на 9-знач. валидации = misleading,
// см. CA-003 + feedback_mock_ui_on_decision_screens).
export function BorrowerCard({
  borrower,
  gnkCertificate,
}: {
  borrower: DossierViewDto["borrower"];
  gnkCertificate: DossierViewDto["gnk_certificate"];
}) {
  const t = useTranslations("dossier.borrower_card");
  return (
    <SectionCard title={t("section_title")} sub={t("section_sub")}>
      {gnkCertificate !== null && <GnkBadge cert={gnkCertificate} />}
      <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-3 text-[13px]">
        <Row label={t("row_legal_form")} value={t(LEGAL_FORM_KEY[borrower.legal_form])} />
        <Row label={t("row_registration")} value={formatRuDate(borrower.registration_date)} />
        <Row
          label={t("row_director")}
          value={
            <>
              {borrower.director_name}
              <span className="ml-1 text-[var(--ink-4)]">
                ·{" "}
                {t("row_director_since", {
                  date: formatRuDate(borrower.director_appointed_at),
                })}
              </span>
            </>
          }
        />
        <Row label={t("row_okved")} value={borrower.oked_main} />
        <Row label={t("row_address")} value={borrower.registered_address} />
        {gnkCertificate !== null && gnkCertificate.cert_id !== null && (
          <Row label={t("row_gnk_cert_id")} value={
            <span className="font-mono">{gnkCertificate.cert_id}</span>
          } />
        )}
      </dl>
    </SectionCard>
  );
}

const STATUS_ICON: Record<GnkStatus, React.ComponentType<{ className?: string }>> = {
  active: CheckCircle2,
  suspended: ShieldAlert,
  revoked: ShieldX,
  unknown: ShieldQuestion,
};

const STATUS_TONE: Record<GnkStatus, string> = {
  active: "bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)] border-[var(--state-ok-border)]",
  suspended:
    "bg-[var(--state-warn-bg)] text-[var(--state-warn-fg)] border-[var(--state-warn-border)]",
  revoked: "bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)] border-[var(--state-bad-border)]",
  unknown:
    "bg-[var(--state-neutral-bg)] text-[var(--state-neutral-fg)] border-[var(--state-neutral-border)]",
};

function GnkBadge({
  cert,
}: {
  cert: NonNullable<DossierViewDto["gnk_certificate"]>;
}) {
  const t = useTranslations("dossier.borrower_card");
  const Icon = STATUS_ICON[cert.status];
  return (
    <div
      className={`mb-3 inline-flex items-center gap-2 rounded-[8px] border px-3 py-1.5 text-[12px] ${STATUS_TONE[cert.status]}`}
      data-testid="gnk-badge"
      data-status={cert.status}
    >
      <Icon className="h-4 w-4" aria-hidden />
      <span>{t(`gnk_status_${cert.status}`)}</span>
      <span className="text-[var(--ink-4)]">·</span>
      <span className="text-[var(--ink-3)]">{t(`gnk_source_${cert.source}`)}</span>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt className="text-[var(--ink-3)]">{label}</dt>
      <dd className="m-0 text-[var(--ink-1)]">{value}</dd>
    </>
  );
}

function formatRuDate(iso: string): string {
  const [yyyy, mm, dd] = iso.split("-");
  return `${dd}.${mm}.${yyyy}`;
}
