"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  MoreHorizontal,
  Plus,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
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

type RecFilter = "all" | "approve" | "review" | "reject";
type DateFilter = "7" | "30" | "90" | "all";

// ────────────────────── Хелперы ──────────────────────

const RU_MONTHS_SHORT = [
  "янв", "фев", "мар", "апр", "май", "июн",
  "июл", "авг", "сен", "окт", "ноя", "дек",
];

function formatRuDate(iso: string): string {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = RU_MONTHS_SHORT[d.getMonth()] ?? "";
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${dd} ${mm} ${yyyy}, ${hh}:${mi}`;
}

function initials(name: string | null): string {
  if (!name) return "—";
  const parts = name.replace(".", " ").split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "—";
}

function pageNumbers(current: number, total: number): Array<number | "gap"> {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "gap", total];
  if (current >= total - 3)
    return [1, "gap", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "gap", current - 1, current, current + 1, "gap", total];
}

function downloadCsv(items: BankDossierListItem[], filename: string): void {
  const headers = ["ИНН", "Название", "Скоринг", "Рекомендация", "Дата", "Аналитик"];
  const rows = items.map((it) => [
    it.borrower_inn_masked,
    `"${it.borrower_name.replace(/"/g, '""')}"`,
    String(it.display_score),
    recommendationLabel(it.recommendation),
    formatRuDate(it.created_at),
    it.analyst_full_name ?? "",
  ]);
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");
  // BOM для Excel — нативно открывает UTF-8.
  const blob = new Blob(["﻿" + csv], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function thresholdDate(filter: DateFilter): Date | null {
  if (filter === "all") return null;
  const days = Number.parseInt(filter, 10);
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d;
}

// ────────────────────── Main view ──────────────────────

export function HistoryView() {
  const router = useRouter();
  const [filter, setFilter] = useState<ListFilter>("mine");
  const [q, setQ] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [recFilter, setRecFilter] = useState<RecFilter>("all");
  const [dateFilter, setDateFilter] = useState<DateFilter>("30");
  const [page, setPage] = useState(1);

  useEffect(() => {
    rememberBackTarget("/history");
  }, []);

  const main = useQuery({
    queryKey: ["bank", "dossiers", { filter, q: appliedQ, page }],
    queryFn: () =>
      listDossiers({ filter, q: appliedQ, page, pageSize: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  // Counts для табов — независимые лёгкие запросы (pageSize=1 → только total).
  const mineCount = useQuery({
    queryKey: ["bank", "dossiers", "count", "mine"],
    queryFn: () => listDossiers({ filter: "mine", page: 1, pageSize: 1 }),
    staleTime: 30_000,
  });
  const allCount = useQuery({
    queryKey: ["bank", "dossiers", "count", "all"],
    queryFn: () => listDossiers({ filter: "all", page: 1, pageSize: 1 }),
    staleTime: 30_000,
  });

  // Client-side recommendation + period filter поверх API-страницы.
  // TODO: вынести в backend параметры — сейчас фильтрация только по
  // загруженной странице, на много страниц counts будут неточны.
  const visibleItems = useMemo(() => {
    if (!main.data) return [];
    const cutoff = thresholdDate(dateFilter);
    return main.data.items.filter((it) => {
      if (recFilter !== "all" && it.recommendation !== recFilter) return false;
      if (cutoff && new Date(it.created_at) < cutoff) return false;
      return true;
    });
  }, [main.data, recFilter, dateFilter]);

  const totalPages = main.data
    ? Math.max(1, Math.ceil(main.data.total / PAGE_SIZE))
    : 1;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(q);
    setPage(1);
  };

  return (
    <>
      <BankPageHead
        title="История проверок"
        subtitle="Все компании, прошедшие через систему — с результатами скоринга и принятыми решениями."
        actions={
          <>
            <button
              type="button"
              onClick={() =>
                downloadCsv(
                  visibleItems,
                  `history-${new Date().toISOString().slice(0, 10)}.csv`,
                )
              }
              disabled={visibleItems.length === 0}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-3 text-[13px] font-medium text-[var(--ub-ink)] transition-colors hover:bg-[var(--ub-surface-2)] disabled:cursor-not-allowed disabled:opacity-55"
            >
              <Download className="size-3.5" />
              Экспорт
            </button>
            <Link
              href="/manual-input"
              className="inline-flex h-9 items-center gap-2 rounded-md bg-[var(--ub-accent)] px-3 text-[13px] font-semibold text-white transition-colors hover:bg-[var(--ub-accent-hover)]"
            >
              <Plus className="size-3.5" />
              Новая заявка
            </Link>
          </>
        }
      />

      <Tabs
        value={filter}
        onChange={(v) => {
          setFilter(v);
          setPage(1);
        }}
        mineCount={mineCount.data?.total ?? null}
        allCount={allCount.data?.total ?? null}
      />

      <Toolbar
        q={q}
        onQ={setQ}
        onSubmit={handleSearch}
        recFilter={recFilter}
        onRecFilter={(v) => {
          setRecFilter(v);
        }}
        dateFilter={dateFilter}
        onDateFilter={(v) => {
          setDateFilter(v);
        }}
      />

      <section className="overflow-hidden rounded-lg border border-[var(--ub-hairline)] bg-[var(--ub-surface)]">
        {main.isLoading ? (
          <SkeletonRows />
        ) : main.isError ? (
          <ErrorBlock
            message={
              main.error instanceof Error
                ? main.error.message
                : "Ошибка загрузки"
            }
          />
        ) : visibleItems.length === 0 ? (
          <EmptyBlock />
        ) : (
          <Table
            items={visibleItems}
            isStale={main.isFetching}
            onRowClick={(id) => router.push(`/dossier/${id}`)}
          />
        )}

        {main.data && main.data.total > 0 ? (
          <Pagination
            page={page}
            totalPages={totalPages}
            shownCount={visibleItems.length}
            apiTotal={main.data.total}
            onSetPage={setPage}
          />
        ) : null}
      </section>
    </>
  );
}

// ────────────────────── Sub-компоненты ──────────────────────

function Tabs({
  value,
  onChange,
  mineCount,
  allCount,
}: {
  value: ListFilter;
  onChange: (v: ListFilter) => void;
  mineCount: number | null;
  allCount: number | null;
}) {
  const items: Array<{ key: ListFilter; label: string; count: number | null }> =
    [
      { key: "mine", label: "Мои", count: mineCount },
      { key: "all", label: "Все", count: allCount },
    ];
  return (
    <div className="mb-5 inline-flex gap-0 rounded-md bg-[var(--ub-surface-3)] p-[3px]">
      {items.map((it) => {
        const active = value === it.key;
        return (
          <button
            key={it.key}
            type="button"
            onClick={() => onChange(it.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-[4px] px-3.5 py-1.5 text-[14px] font-medium transition-colors",
              active
                ? "bg-white text-[var(--ub-ink)] shadow-[0_1px_1px_rgba(15,23,42,0.04)]"
                : "text-[var(--ub-ink-2)] hover:text-[var(--ub-ink)]",
            )}
          >
            {it.label}
            {it.count != null ? (
              <span
                className={cn(
                  "rounded px-1.5 py-px text-[11px]",
                  active
                    ? "bg-[var(--ub-surface-2)] text-[var(--ub-ink-3)]"
                    : "bg-[var(--ub-surface-3)] text-[var(--ub-ink-3)]",
                )}
              >
                {it.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

function Toolbar({
  q,
  onQ,
  onSubmit,
  recFilter,
  onRecFilter,
  dateFilter,
  onDateFilter,
}: {
  q: string;
  onQ: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  recFilter: RecFilter;
  onRecFilter: (v: RecFilter) => void;
  dateFilter: DateFilter;
  onDateFilter: (v: DateFilter) => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
      <form onSubmit={onSubmit} className="flex-1" style={{ maxWidth: 480 }}>
        <div className="relative flex items-center">
          <Search className="pointer-events-none absolute left-3 size-4 text-[var(--ub-ink-4)]" />
          <input
            type="search"
            placeholder="Поиск по ИНН или названию компании"
            value={q}
            onChange={(e) => onQ(e.target.value)}
            className="h-[38px] w-full rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-9 text-[14px] text-[var(--ub-ink)] outline-none transition-colors placeholder:text-[var(--ub-ink-4)] focus:border-[var(--ub-accent)] focus:shadow-[0_0_0_3px_var(--ub-accent-ring)]"
          />
          {q ? (
            <button
              type="button"
              onClick={() => onQ("")}
              aria-label="Очистить"
              className="absolute right-2 grid size-[22px] place-items-center rounded text-[var(--ub-ink-4)] hover:bg-[var(--ub-surface-2)] hover:text-[var(--ub-ink-2)]"
            >
              <X className="size-3.5" />
            </button>
          ) : null}
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-3">
        <FilterSelect
          label="Рекомендация"
          value={recFilter}
          onChange={(v) => onRecFilter(v as RecFilter)}
          options={[
            { v: "all", l: "Все" },
            { v: "approve", l: "К выдаче" },
            { v: "review", l: "На проверку" },
            { v: "reject", l: "Отклонить" },
          ]}
        />
        <FilterSelect
          label="Период"
          value={dateFilter}
          onChange={(v) => onDateFilter(v as DateFilter)}
          options={[
            { v: "7", l: "7 дней" },
            { v: "30", l: "30 дней" },
            { v: "90", l: "90 дней" },
            { v: "all", l: "Всё время" },
          ]}
        />
        <button
          type="button"
          title="Дополнительные фильтры"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-2.5 text-[13px] text-[var(--ub-ink-2)] transition-colors hover:bg-[var(--ub-surface-2)] hover:text-[var(--ub-ink)]"
        >
          <Filter className="size-3.5 text-[var(--ub-ink-4)]" />
          Ещё
        </button>
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ v: string; l: string }>;
  onChange: (v: string) => void;
}) {
  const current = options.find((o) => o.v === value) ?? options[0];
  return (
    <label className="relative inline-flex h-8 items-center gap-1.5 rounded-md border border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-2.5 text-[13px] text-[var(--ub-ink-2)] transition-colors hover:bg-[var(--ub-surface-2)] hover:text-[var(--ub-ink)]">
      <span className="text-[12px] text-[var(--ub-ink-3)]">{label}:</span>
      <span className="text-[var(--ub-ink)]">{current?.l ?? ""}</span>
      <ChevronDown className="size-3.5 text-[var(--ub-ink-4)]" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="absolute inset-0 cursor-pointer opacity-0"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v}>
            {o.l}
          </option>
        ))}
      </select>
    </label>
  );
}

function Table({
  items,
  isStale,
  onRowClick,
}: {
  items: BankDossierListItem[];
  isStale: boolean;
  onRowClick: (id: string) => void;
}) {
  return (
    <div className={cn("transition-opacity", isStale && "opacity-70")}>
      <table className="w-full border-collapse text-[14px]">
        <thead>
          <tr>
            <Th width={150}>ИНН</Th>
            <Th>Название компании</Th>
            <Th width={180}>Скоринг</Th>
            <Th width={160}>Рекомендация</Th>
            <Th width={180}>Дата</Th>
            <Th width={170}>Аналитик</Th>
            <Th width={40} />
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <Row key={it.dossier_id} item={it} onClick={() => onRowClick(it.dossier_id)} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, width }: { children?: React.ReactNode; width?: number }) {
  return (
    <th
      style={width ? { width } : undefined}
      className="border-b border-[var(--ub-hairline)] bg-[var(--ub-surface-2)] px-4 py-2.5 text-left text-[12px] font-medium tracking-[0.01em] whitespace-nowrap text-[var(--ub-ink-3)]"
    >
      {children}
    </th>
  );
}

function Row({
  item,
  onClick,
}: {
  item: BankDossierListItem;
  onClick: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className="cursor-pointer border-b border-[var(--ub-hairline-soft)] transition-colors last:border-b-0 hover:bg-[var(--ub-surface-2)]"
    >
      <td className="px-4 py-3.5 font-mono tabular-nums text-[13px] text-[var(--ub-ink)]">
        {item.borrower_inn_masked}
      </td>
      <td className="px-4 py-3.5 font-medium text-[var(--ub-ink)]">
        {item.borrower_name}
      </td>
      <td className="px-4 py-3.5">
        <ScoreBar score={item.display_score} />
      </td>
      <td className="px-4 py-3.5">
        <RecBadge rec={item.recommendation} />
      </td>
      <td className="px-4 py-3.5 text-[13px] text-[var(--ub-ink-3)]">
        {formatRuDate(item.created_at)}
      </td>
      <td className="px-4 py-3.5">
        <AnalystCell name={item.analyst_full_name} />
      </td>
      <td className="px-4 py-3.5">
        <button
          type="button"
          aria-label="Действия"
          onClick={(e) => {
            e.stopPropagation();
            // TODO: контекстное меню (открыть, дублировать, экспортировать)
          }}
          className="grid size-7 place-items-center rounded text-[var(--ub-ink-3)] hover:bg-[var(--ub-surface-3)] hover:text-[var(--ub-ink)]"
        >
          <MoreHorizontal className="size-4" />
        </button>
      </td>
    </tr>
  );
}

function ScoreBar({ score }: { score: number }) {
  const band = scoreBand(score) ?? "warn";
  const fill: Record<"good" | "warn" | "bad", string> = {
    good: "#059669",
    warn: "#D97706",
    bad: "#DC2626",
  };
  return (
    <span className="inline-flex items-center gap-2.5 tabular-nums">
      <span className="min-w-[28px] font-semibold text-[var(--ub-ink)]">
        {score}
      </span>
      <span className="block h-1 w-24 overflow-hidden rounded-full bg-[var(--ub-surface-3)]">
        <span
          className="block h-full rounded-full"
          style={{
            width: `${Math.min(100, Math.max(0, score))}%`,
            background: fill[band],
          }}
        />
      </span>
    </span>
  );
}

function RecBadge({ rec }: { rec: BankDossierListItem["recommendation"] }) {
  const band = recommendationBand(rec);
  const colors: Record<"good" | "warn" | "bad", { fg: string; bg: string }> = {
    good: { fg: "var(--ub-ok-fg)", bg: "var(--ub-ok-bg)" },
    warn: { fg: "var(--ub-warn-fg)", bg: "var(--ub-warn-bg)" },
    bad: { fg: "var(--ub-bad-fg)", bg: "var(--ub-bad-bg)" },
  };
  const c = colors[band];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[13px] font-medium whitespace-nowrap"
      style={{ color: c.fg, background: c.bg }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ background: c.fg }}
        aria-hidden
      />
      {recommendationLabel(rec)}
    </span>
  );
}

function AnalystCell({ name }: { name: string | null }) {
  if (!name) {
    return <span className="text-[13px] text-[var(--ub-ink-4)]">—</span>;
  }
  return (
    <span className="inline-flex items-center gap-2">
      <span className="grid size-[22px] shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#D88E73] to-[#B5624A] text-[10px] font-semibold text-white">
        {initials(name)}
      </span>
      <span className="text-[13px] text-[var(--ub-ink)]">{name}</span>
    </span>
  );
}

function Pagination({
  page,
  totalPages,
  shownCount,
  apiTotal,
  onSetPage,
}: {
  page: number;
  totalPages: number;
  shownCount: number;
  apiTotal: number;
  onSetPage: (p: number) => void;
}) {
  const pages = pageNumbers(page, totalPages);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--ub-hairline)] bg-[var(--ub-surface)] px-4 py-3 text-[13px] text-[var(--ub-ink-3)]">
      <span>
        Показано <b className="text-[var(--ub-ink)]">{shownCount}</b> из{" "}
        <b className="text-[var(--ub-ink)]">{apiTotal}</b>
      </span>
      <div className="flex items-center gap-1">
        <PageBtn
          disabled={page <= 1}
          onClick={() => onSetPage(page - 1)}
          aria-label="Назад"
        >
          <ChevronLeft className="size-3.5" />
        </PageBtn>
        {pages.map((p, i) =>
          p === "gap" ? (
            <span
              key={`gap-${i}`}
              className="px-1.5 text-[var(--ub-ink-4)]"
            >
              …
            </span>
          ) : (
            <PageBtn
              key={p}
              active={p === page}
              onClick={() => onSetPage(p)}
            >
              {p}
            </PageBtn>
          ),
        )}
        <PageBtn
          disabled={page >= totalPages}
          onClick={() => onSetPage(page + 1)}
          aria-label="Вперёд"
        >
          <ChevronRight className="size-3.5" />
        </PageBtn>
      </div>
    </div>
  );
}

function PageBtn({
  children,
  active,
  disabled,
  onClick,
  ...rest
}: {
  children: React.ReactNode;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
} & React.AriaAttributes) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-7 min-w-[28px] items-center justify-center rounded px-2 text-[13px] font-medium tabular-nums transition-colors",
        active
          ? "bg-[var(--ub-ink)] text-white hover:bg-[var(--ub-ink)]"
          : "bg-transparent text-[var(--ub-ink-2)] hover:bg-[var(--ub-surface-2)] hover:text-[var(--ub-ink)]",
        disabled && "cursor-not-allowed opacity-40 hover:bg-transparent",
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

function SkeletonRows() {
  return (
    <div className="space-y-3 p-5">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-10 animate-pulse rounded-md bg-[var(--ub-surface-2)]"
        />
      ))}
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="px-5 py-10 text-center text-[13px] text-[var(--ub-bad-fg)]">
      Не удалось загрузить историю: {message}
    </div>
  );
}

function EmptyBlock() {
  return (
    <div className="px-5 py-12 text-center text-[13px] text-[var(--ub-ink-3)]">
      Ничего не найдено по текущим фильтрам.
    </div>
  );
}
