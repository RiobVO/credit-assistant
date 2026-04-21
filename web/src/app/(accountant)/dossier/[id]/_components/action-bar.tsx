"use client";

import { ChevronLeft, Download } from "lucide-react";
import { useRouter } from "next/navigation";

import { API_URL } from "@/lib/config";

type Props = {
  dossierId: string;
};

export function ActionBar({ dossierId }: Props) {
  const router = useRouter();
  const pdfHref = `${API_URL}/api/dossier/${dossierId}/pdf`;

  return (
    <div className="mt-7 flex items-center justify-between border-t border-[var(--ca-border)] pt-5">
      <button
        type="button"
        onClick={() => router.push("/manual-input")}
        className="inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]"
      >
        <ChevronLeft className="size-4" />
        Назад к списку
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
