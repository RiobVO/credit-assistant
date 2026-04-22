"use client";

import { ArrowUpRight, FileText, UserPlus, UserSearch } from "lucide-react";
import Link from "next/link";

import type { BorrowerSearchResult } from "@/lib/bank-api";
import { scoreBand } from "@/lib/bank-api";
import { cn } from "@/lib/utils";

const BAND_BADGE: Record<"good" | "warn" | "bad", string> = {
  good: "bg-[#DCFCE7] text-[#15803D] border-[#A7F3D0]",
  warn: "bg-[#FEF3C7] text-[#A16207] border-[#FCD34D]",
  bad: "bg-[#FEE2E2] text-[#B91C1C] border-[#FCA5A5]",
};

function formatCreatedAt(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SearchResult({
  result,
  inn,
}: {
  result: BorrowerSearchResult;
  inn: string;
}) {
  if (result.found && result.dossier_id) {
    return <FoundWithDossier result={result} />;
  }
  if (result.found) {
    return <BorrowerWithoutDossier name={result.borrower_name ?? "—"} inn={inn} />;
  }
  return <NotFound inn={inn} />;
}

function FoundWithDossier({ result }: { result: BorrowerSearchResult }) {
  const band = scoreBand(result.display_score) ?? "warn";
  return (
    <div className="rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2 text-[11px] font-medium tracking-[0.5px] text-[#15803D] uppercase">
            <span className="inline-block size-1.5 rounded-full bg-[#15803D]" />
            Досье найдено
          </div>
          <h2 className="text-[18px] font-semibold text-[var(--ca-text-strong)]">
            {result.borrower_name}
          </h2>
          {result.created_at && (
            <p className="mt-1 text-[12.5px] text-[var(--ca-text-muted)]">
              Последнее досье: {formatCreatedAt(result.created_at)}
            </p>
          )}
        </div>
        <div
          className={cn(
            "rounded-full border px-3 py-1 text-[12px] font-semibold whitespace-nowrap",
            BAND_BADGE[band],
          )}
          title="Score (выше = лучше)"
        >
          Score {result.display_score ?? "—"}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href={`/dossier/${result.dossier_id}`}
          className="inline-flex items-center gap-2 rounded-md bg-[#1E40AF] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[#1A3899]"
        >
          <FileText className="size-4" />
          Открыть досье
          <ArrowUpRight className="size-4" />
        </Link>
        <Link
          href="/manual-input"
          className="inline-flex items-center gap-2 rounded-md border border-[var(--ca-line)] bg-white px-4 py-2 text-[13px] font-medium text-[var(--ca-text-strong)] transition hover:bg-[var(--ca-bg-soft)]"
        >
          Пересобрать с новыми выгрузками
        </Link>
      </div>
    </div>
  );
}

function BorrowerWithoutDossier({ name, inn }: { name: string; inn: string }) {
  return (
    <div className="rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm">
      <div className="mb-1 flex items-center gap-2 text-[11px] font-medium tracking-[0.5px] text-[#A16207] uppercase">
        <UserSearch className="size-3.5" />
        Заёмщик есть, досье не сформировано
      </div>
      <h2 className="text-[18px] font-semibold text-[var(--ca-text-strong)]">
        {name}
      </h2>
      <p className="mt-1 text-[12.5px] text-[var(--ca-text-muted)]">
        ИНН <span className="font-mono">{inn}</span> найден в базе, но bank-mode досье ещё не создавалось.
      </p>
      <Link
        href={`/manual-input?inn=${encodeURIComponent(inn)}`}
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-[#1E40AF] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[#1A3899]"
      >
        Загрузить выгрузки <ArrowUpRight className="size-4" />
      </Link>
    </div>
  );
}

function NotFound({ inn }: { inn: string }) {
  return (
    <div className="rounded-lg border border-[var(--ca-line)] bg-white p-6 shadow-sm">
      <div className="mb-1 flex items-center gap-2 text-[11px] font-medium tracking-[0.5px] text-[var(--ca-text-muted)] uppercase">
        <UserPlus className="size-3.5" />
        Новый заёмщик
      </div>
      <h2 className="text-[18px] font-semibold text-[var(--ca-text-strong)]">
        Не найден в системе
      </h2>
      <p className="mt-1 text-[12.5px] text-[var(--ca-text-muted)]">
        ИНН <span className="font-mono">{inn}</span> не встречался. Загрузите
        выгрузки Soliq (декларация + ilova) или заполните вручную.
      </p>
      <Link
        href={`/manual-input?inn=${encodeURIComponent(inn)}`}
        className="mt-5 inline-flex items-center gap-2 rounded-md bg-[#1E40AF] px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[#1A3899]"
      >
        Загрузить выгрузки <ArrowUpRight className="size-4" />
      </Link>
    </div>
  );
}
