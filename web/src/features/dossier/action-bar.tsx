"use client";

import { ChevronLeft, Download } from "lucide-react";
import Link from "next/link";

import { APP_MODE } from "@/lib/config";

type Props = {
  dossierId: string;
};

// Mode-aware actions. PDF идёт через Next BFF (same-origin) — это нужно
// в bank-режиме, где backend требует Bearer, и не мешает в accountant.
export function ActionBar({ dossierId }: Props) {
  const pdfHref = `/api/dossier/${dossierId}/pdf`;
  const back =
    APP_MODE === "bank"
      ? { href: "/history", label: "К истории" }
      : { href: "/manual-input", label: "Назад" };

  return (
    <div className="mt-7 flex items-center justify-between border-t border-[var(--ca-border)] pt-5">
      <Link
        href={back.href}
        className="inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]"
      >
        <ChevronLeft className="size-4" />
        {back.label}
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
  );
}
