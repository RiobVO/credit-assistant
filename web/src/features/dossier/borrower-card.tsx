"use client";

import { CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";

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

export function BorrowerCard({ borrower }: { borrower: DossierViewDto["borrower"] }) {
  const t = useTranslations("dossier.borrower_card");
  return (
    <div className="flex h-full flex-col rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-start justify-between border-b border-[var(--border)] px-[22px] py-4">
        <div>
          <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ink-4)] uppercase">
            {t("title")}
          </div>
          <h3 className="m-0 mt-1 text-[16px] font-semibold tracking-[-0.2px] text-[var(--ink-1)]">
            {borrower.name}
          </h3>
          <p className="m-0 mt-0.5 font-mono text-[12px] text-[var(--ink-3)]">
            {t("inn_prefix", { inn: borrower.inn })}
          </p>
        </div>

        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#BFE2D2] bg-[var(--state-ok-bg)] px-2.5 py-1 text-[11px] font-semibold text-[var(--state-ok-fg)]">
          <CheckCircle2 className="size-3.5" />
          {t("verified")}
        </span>
      </header>

      <dl className="grid flex-1 grid-cols-[140px_1fr] gap-x-4 gap-y-3 px-[22px] py-4 text-[13px]">
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
