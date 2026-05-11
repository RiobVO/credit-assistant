"use client";

import { ChevronLeft, Download, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { rememberStep1Prefill } from "@/features/manual-input/prefill";
import type { DossierViewDto } from "@/lib/api";
import { APP_MODE } from "@/lib/config";

import { consumeBackTarget } from "./back-target";

type Props = {
  dossierId: string;
  borrower: DossierViewDto["borrower"];
};

const BUTTON_GHOST =
  "inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]";

// CA-055: smart back (sessionStorage с /search или /history).
// CA-056: «Пересобрать» — ведёт на /manual-input?inn=<INN>.
// CA-058: pre-fill Шага 1 при «Пересобрать» — borrower-карточка тянется
// из досье через sessionStorage. Финансы (Шаг 2) и кредит (Шаг 3) —
// аналитик заполняет заново, в этом и смысл «Пересобрать».
export function ActionBar({ dossierId, borrower }: Props) {
  const router = useRouter();
  const pdfHref = `/api/dossier/${dossierId}/pdf`;
  const rebuildHref = `/manual-input?inn=${encodeURIComponent(borrower.inn)}`;

  const handleBack = () => {
    if (APP_MODE === "bank") {
      const target = consumeBackTarget() ?? "/history";
      router.push(target);
      return;
    }
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/manual-input");
    }
  };

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
    router.push(rebuildHref);
  };

  return (
    <div className="mt-7 flex items-center justify-between gap-3 border-t border-[var(--ca-border)] pt-5">
      <button type="button" onClick={handleBack} className={BUTTON_GHOST}>
        <ChevronLeft className="size-4" />
        Назад
      </button>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleRebuild}
          className={BUTTON_GHOST}
          title="Создать новое досье с дополнительными выгрузками. Карточка заёмщика подставится автоматически; финансы и параметры кредита нужно заполнить заново. Существующее досье остаётся в истории."
        >
          <RefreshCw className="size-4" />
          Пересобрать с дополнениями
        </button>

        <a
          href={pdfHref}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-[38px] items-center gap-2 rounded-md bg-[var(--ca-primary-blue)] px-5 text-[13.5px] font-semibold text-white transition-colors hover:bg-[var(--ca-primary-blue-700)]"
        >
          <Download className="size-4" />
          Скачать PDF
        </a>
      </div>
    </div>
  );
}
