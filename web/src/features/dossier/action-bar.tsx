"use client";

import { ChevronLeft, Download, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { APP_MODE } from "@/lib/config";

import { consumeBackTarget } from "./back-target";

type Props = {
  dossierId: string;
  borrowerInn: string;
};

const BACK_BUTTON_CLASS =
  "inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]";

const SECONDARY_BUTTON_CLASS =
  "inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]";

// CA-055: smart back (sessionStorage с /search или /history).
// CA-056: «Пересобрать» — ведёт на /manual-input?inn=<INN> с pre-filled
// ИНН. Существующее досье остаётся (аудит), создаётся новое с дополненными
// данными. Аналог кнопки «Пересобрать с новыми выгрузками» с /search.
export function ActionBar({ dossierId, borrowerInn }: Props) {
  const router = useRouter();
  const pdfHref = `/api/dossier/${dossierId}/pdf`;
  const rebuildHref = `/manual-input?inn=${encodeURIComponent(borrowerInn)}`;

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

  return (
    <div className="mt-7 flex items-center justify-between gap-3 border-t border-[var(--ca-border)] pt-5">
      <button type="button" onClick={handleBack} className={BACK_BUTTON_CLASS}>
        <ChevronLeft className="size-4" />
        Назад
      </button>

      <div className="flex items-center gap-3">
        <Link
          href={rebuildHref}
          className={SECONDARY_BUTTON_CLASS}
          title="Создать новое досье с дополнительными выгрузками. Существующее досье остаётся в истории."
        >
          <RefreshCw className="size-4" />
          Пересобрать с дополнениями
        </Link>

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
