"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowUpRight, ChevronLeft, ChevronRight, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { rememberBackTarget } from "@/features/dossier/back-target";
import {
  type BankDossierListItem,
  type ListFilter,
  listDossiers,
  recommendationBand,
  recommendationLabel,
  scoreBand,
} from "@/lib/bank-api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

const BAND_BADGE: Record<"good" | "warn" | "bad", string> = {
  good: "bg-[#DCFCE7] text-[#15803D] border-[#A7F3D0]",
  warn: "bg-[#FEF3C7] text-[#A16207] border-[#FCD34D]",
  bad: "bg-[#FEE2E2] text-[#B91C1C] border-[#FCA5A5]",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function HistoryView() {
  const [filter, setFilter] = useState<ListFilter>("all");
  const [q, setQ] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [page, setPage] = useState(1);

  // CA-055: запоминаем как back-target для досье — открыл досье, нажал
  // «Назад» → вернёшься сюда, а не на промежуточный /manual-input.
  useEffect(() => {
    rememberBackTarget("/history");
  }, []);

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ["bank", "dossiers", { filter, q: appliedQ, page }],
    queryFn: () =>
      listDossiers({ filter, q: appliedQ, page, pageSize: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(q);
    setPage(1);
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="rounded-lg border border-[var(--ca-line)] bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--ca-line)] px-5 py-4">
        <FilterTabs
          value={filter}
          onChange={(f) => {
            setFilter(f);
            setPage(1);
          }}
        />
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-[var(--ca-text-muted)]" />
            <input
              type="search"
              placeholder="ИНН или название"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="w-[260px] rounded-md border border-[var(--ca-line)] bg-[var(--ca-bg-soft)] py-1.5 pr-3 pl-9 text-[13px] outline-none transition focus:border-[#1E40AF] focus:ring-1 focus:ring-[#1E40AF]/40"
            />
          </div>
          <button
            type="submit"
            className="rounded-md border border-[var(--ca-line)] bg-white px-3 py-1.5 text-[12.5px] font-medium text-[var(--ca-text-strong)] transition hover:bg-[var(--ca-bg-soft)]"
          >
            Найти
          </button>
        </form>
      </div>

      {isLoading ? (
        <SkeletonRows />
      ) : isError ? (
        <ErrorBlock message={error instanceof Error ? error.message : "Ошибка"} />
      ) : !data || data.items.length === 0 ? (
        <EmptyBlock q={appliedQ} filter={filter} />
      ) : (
        <Table items={data.items} isStale={isFetching} />
      )}

      {data && data.total > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={data.total}
          pageSize={PAGE_SIZE}
          onPrev={() => setPage((p) => Math.max(1, p - 1))}
          onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
        />
      )}
    </section>
  );
}

function FilterTabs({
  value,
  onChange,
}: {
  value: ListFilter;
  onChange: (v: ListFilter) => void;
}) {
  const items: Array<{ key: ListFilter; label: string }> = [
    { key: "all", label: "Все" },
    { key: "mine", label: "Мои" },
  ];
  return (
    <div className="inline-flex rounded-md border border-[var(--ca-line)] bg-[var(--ca-bg-soft)] p-0.5">
      {items.map((it) => (
        <button
          key={it.key}
          type="button"
          onClick={() => onChange(it.key)}
          className={cn(
            "rounded-[5px] px-4 py-1.5 text-[12.5px] font-medium transition",
            value === it.key
              ? "bg-white text-[var(--ca-text-strong)] shadow-sm"
              : "text-[var(--ca-text-muted)] hover:text-[var(--ca-text-strong)]",
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

function Table({
  items,
  isStale,
}: {
  items: BankDossierListItem[];
  isStale: boolean;
}) {
  return (
    <div className={cn("overflow-x-auto transition-opacity", isStale && "opacity-70")}>
      <table className="w-full text-[13px]">
        <thead className="bg-[var(--ca-bg-soft)] text-left text-[11.5px] font-medium tracking-[0.5px] text-[var(--ca-text-muted)] uppercase">
          <tr>
            <th className="px-5 py-3">ИНН</th>
            <th className="px-3 py-3">Заёмщик</th>
            <th className="px-3 py-3">Score</th>
            <th className="px-3 py-3">Рекомендация</th>
            <th className="px-3 py-3">Аналитик</th>
            <th className="px-3 py-3">Создано</th>
            <th className="px-5 py-3" />
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--ca-line)]">
          {items.map((it) => (
            <Row key={it.dossier_id} item={it} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Row({ item }: { item: BankDossierListItem }) {
  const band = scoreBand(item.display_score) ?? "warn";
  const recBand = recommendationBand(item.recommendation);
  return (
    <tr className="transition hover:bg-[var(--ca-bg-soft)]">
      <td className="px-5 py-3 font-mono text-[12.5px] text-[var(--ca-text-strong)]">
        {item.borrower_inn_masked}
      </td>
      <td className="px-3 py-3 text-[var(--ca-text-strong)]">{item.borrower_name}</td>
      <td className="px-3 py-3">
        <span
          className={cn(
            "inline-block rounded-full border px-2 py-0.5 text-[11.5px] font-semibold",
            BAND_BADGE[band],
          )}
        >
          {item.display_score}
        </span>
      </td>
      <td className="px-3 py-3">
        <span
          className={cn(
            "inline-block rounded-full border px-2 py-0.5 text-[11.5px] font-medium",
            BAND_BADGE[recBand],
          )}
        >
          {recommendationLabel(item.recommendation)}
        </span>
      </td>
      <td className="px-3 py-3 text-[12.5px] text-[var(--ca-text-muted)]">
        {item.analyst_full_name ?? "—"}
      </td>
      <td className="px-3 py-3 text-[12.5px] whitespace-nowrap text-[var(--ca-text-muted)]">
        {formatDate(item.created_at)}
      </td>
      <td className="px-5 py-3 text-right">
        <Link
          href={`/dossier/${item.dossier_id}`}
          className="inline-flex items-center gap-1 text-[12.5px] font-medium text-[#1E40AF] hover:underline"
        >
          Открыть <ArrowUpRight className="size-3.5" />
        </Link>
      </td>
    </tr>
  );
}

function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <div className="flex items-center justify-between border-t border-[var(--ca-line)] px-5 py-3 text-[12.5px] text-[var(--ca-text-muted)]">
      <span>
        {from}–{to} из {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onPrev}
          disabled={page <= 1}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--ca-line)] bg-white px-2.5 py-1 text-[12px] text-[var(--ca-text-strong)] transition hover:bg-[var(--ca-bg-soft)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ChevronLeft className="size-3.5" />
          Назад
        </button>
        <span className="px-2 text-[12px]">
          Стр {page} из {totalPages}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= totalPages}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--ca-line)] bg-white px-2.5 py-1 text-[12px] text-[var(--ca-text-strong)] transition hover:bg-[var(--ca-bg-soft)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Вперёд
          <ChevronRight className="size-3.5" />
        </button>
      </div>
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-3 p-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-10 animate-pulse rounded-md bg-[var(--ca-bg-soft)]"
        />
      ))}
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="px-5 py-10 text-center">
      <p className="text-[13px] text-[#B91C1C]">Не удалось загрузить историю: {message}</p>
    </div>
  );
}

function EmptyBlock({ q, filter }: { q: string; filter: ListFilter }) {
  return (
    <div className="px-5 py-12 text-center text-[var(--ca-text-muted)]">
      <p className="text-[13.5px] font-medium text-[var(--ca-text-strong)]">
        Досье не найдены
      </p>
      <p className="mt-1 text-[12.5px]">
        {q
          ? `Не нашли совпадений по «${q}»`
          : filter === "mine"
            ? "Вы пока не создавали ни одного досье."
            : "В системе ещё нет bank-mode досье."}
      </p>
    </div>
  );
}
