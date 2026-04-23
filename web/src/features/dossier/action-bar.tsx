"use client";

import { ChevronLeft, Download } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { APP_MODE } from "@/lib/config";

type Props = {
  dossierId: string;
};

const BACK_BUTTON_CLASS =
  "inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]";

// Mode-aware actions. PDF идёт через Next BFF (same-origin) — это нужно
// в bank-режиме, где backend требует Bearer, и не мешает в accountant.
//
// Bank-режим: фиксированный «К истории» (там есть /history page).
// Accountant: history-aware back — возвращает откуда пришёл (search /
// /manual-input / прямой URL). Fallback на /manual-input для прямого захода.
export function ActionBar({ dossierId }: Props) {
  const router = useRouter();
  const pdfHref = `/api/dossier/${dossierId}/pdf`;

  const handleAccountantBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/manual-input");
    }
  };

  return (
    <div className="mt-7 flex items-center justify-between border-t border-[var(--ca-border)] pt-5">
      {APP_MODE === "bank" ? (
        <Link href="/history" className={BACK_BUTTON_CLASS}>
          <ChevronLeft className="size-4" />
          К истории
        </Link>
      ) : (
        <button type="button" onClick={handleAccountantBack} className={BACK_BUTTON_CLASS}>
          <ChevronLeft className="size-4" />
          Назад
        </button>
      )}

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
