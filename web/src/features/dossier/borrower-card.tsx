"use client";

import { useTranslations } from "next-intl";

import { SectionCard } from "@/components/section-card";
import type { DossierViewDto } from "@/lib/api";

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

// Phase 9 design statement: SectionCard shell без icon-tile (banking-минимализм
// для read-only data). Verified-pill «Проверено в ГНК» убран до закрытия CA-003
// (real ГНК lookup) — pill по 9-знач. валидации формата = misleading на screen
// принятия решения; вернём после hybrid public-lookup + manual upload справки.
export function BorrowerCard({ borrower }: { borrower: DossierViewDto["borrower"] }) {
  const t = useTranslations("dossier.borrower_card");
  return (
    <SectionCard title={t("section_title")} sub={t("section_sub")}>
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
        <Row label={t("row_okved")} value={borrower.okved_main} />
        <Row label={t("row_address")} value={borrower.registered_address} />
      </dl>
    </SectionCard>
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
