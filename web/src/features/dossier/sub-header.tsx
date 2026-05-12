"use client";

import { Download, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { rememberStep1Prefill } from "@/features/manual-input/prefill";
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

export function SubHeader({
  dossierId,
  borrower,
}: {
  dossierId: string;
  borrower: DossierViewDto["borrower"];
}) {
  const t = useTranslations("dossier.sub_header");
  const tBorrower = useTranslations("dossier.borrower_card");
  const router = useRouter();
  const pdfHref = `/api/dossier/${dossierId}/pdf`;

  const handleRebuild = () => {
    rememberStep1Prefill({
      inn: borrower.inn,
      name: borrower.name,
      legal_form: borrower.legal_form,
      registration_date: borrower.registration_date,
      director_name: borrower.director_name,
      director_appointed_at: borrower.director_appointed_at,
      okved_main: borrower.okved_main,
      registered_address: borrower.registered_address,
    });
    router.push(`/manual-input?inn=${encodeURIComponent(borrower.inn)}`);
  };

  const legalLabel = tBorrower(LEGAL_FORM_KEY[borrower.legal_form]);
  const meta = [
    t("meta_inn", { inn: borrower.inn }),
    t("meta_legal_form", { form: legalLabel }),
    t("meta_okved", { code: borrower.okved_main }),
  ].join(" · ");

  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
      <div className="min-w-0">
        <h1 className="m-0 text-[26px] font-semibold tracking-[-0.4px] text-[var(--ink-1)]">
          {borrower.name}
        </h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--ink-3)]">{meta}</p>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={handleRebuild}
          className="inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 text-[13.5px] font-semibold text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)]"
        >
          <RefreshCw className="size-4" />
          {t("action_rebuild")}
        </button>
        <a
          href={pdfHref}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-[38px] items-center gap-2 rounded-md bg-[var(--brand-primary)] px-5 text-[13.5px] font-semibold text-white transition-colors hover:bg-[var(--brand-primary-hover)]"
        >
          <Download className="size-4" />
          {t("action_download_pdf")}
        </a>
      </div>
    </div>
  );
}
