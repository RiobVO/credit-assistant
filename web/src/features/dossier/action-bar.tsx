"use client";

import { ChevronLeft, Download } from "lucide-react";
import { useRouter } from "next/navigation";

import { APP_MODE } from "@/lib/config";

import { consumeBackTarget } from "./back-target";

type Props = {
  dossierId: string;
};

const BACK_BUTTON_CLASS =
  "inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]";

// CA-055: smart back. Раньше router.back() слепо шёл на предыдущую entry,
// и если ей был `/manual-input?draft=X` после submit — аналитик попадал
// на пустую форму (draft удалён в БД). Теперь читаем «откуда я пришёл»
// из sessionStorage (`/search` или `/history` пишут себя при mount),
// fallback по APP_MODE если sessionStorage пуст (прямой URL / новая
// вкладка). router.push с известным path, не back() — предсказуемо.
//
// Accountant-режим оставлен на back() — там нет двух «список»-страниц
// (только /manual-input и /dossier), back туда и нужен.
export function ActionBar({ dossierId }: Props) {
  const router = useRouter();
  const pdfHref = `/api/dossier/${dossierId}/pdf`;

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
    <div className="mt-7 flex items-center justify-between border-t border-[var(--ca-border)] pt-5">
      <button type="button" onClick={handleBack} className={BACK_BUTTON_CLASS}>
        <ChevronLeft className="size-4" />
        Назад
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
  );
}
