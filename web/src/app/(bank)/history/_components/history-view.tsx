"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSearch,
  Search,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { BankPageHead } from "@/app/(bank)/_components/page-head";
import { LiveStrip } from "@/features/search/live-strip";

// Pure decoration — lazy-load, без SSR (тогда нет flash при route mount).
const GridPattern = dynamic(
  () => import("@/features/search/grid-pattern").then((m) => m.GridPattern),
  { ssr: false },
);
import {
  formatRelativeTime,
  isFreshTime,
} from "@/features/history/relative-time";
import {
  type BankDossierListItem,
  type ListFilter,
  listDossiers,
  recommendationBand,
  scoreBand,
} from "@/lib/bank-api";
import type { Recommendation } from "@/lib/api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

type RecFilter = "all" | "approve" | "review" | "reject";
type DateFilter = "7" | "30" | "90" | "all";
type ScoreTone = "good" | "warn" | "bad";

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

function downloadCsv(
  items: BankDossierListItem[],
  filename: string,
  headers: string[],
  recLabel: (rec: Recommendation) => string,
): void {
  const rows = items.map((it) => [
    it.borrower_inn_masked,
    `"${it.borrower_name.replace(/"/g, '""')}"`,
    String(it.display_score),
    recLabel(it.recommendation),
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

export function HistoryView() {
  const router = useRouter();
  const t = useTranslations("bank.history");
  const [filter, setFilter] = useState<ListFilter>("mine");
  const [q, setQ] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [recFilter, setRecFilter] = useState<RecFilter>("all");
  const [dateFilter, setDateFilter] = useState<DateFilter>("30");
  const [page, setPage] = useState(1);

  const main = useQuery({
    queryKey: ["bank", "dossiers", { filter, q: appliedQ, page }],
    queryFn: () =>
      listDossiers({ filter, q: appliedQ, page, pageSize: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

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

  // Filtering recommendation + period — пока client-side (TODO: backend).
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

  const apiHasZero = main.data ? main.data.total === 0 : false;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedQ(q);
    setPage(1);
  };

  return (
    <>
      <GridPattern tone="brand" />
      <div className="relative z-[1]">
      <BankPageHead
        title={t("title")}
        subtitle={t("subtitle")}
        actions={
          <button
            type="button"
            onClick={() =>
              downloadCsv(
                visibleItems,
                `history-${new Date().toISOString().slice(0, 10)}.csv`,
                [
                  t("col_inn"),
                  t("col_company"),
                  t("col_score"),
                  t("col_recommendation"),
                  t("col_date"),
                  t("col_analyst"),
                ],
                (rec) => t(`rec_${rec}`),
              )
            }
            disabled={visibleItems.length === 0}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3.5 text-[13px] font-medium text-[var(--ink-1)] transition-colors hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            <Download className="size-3.5" />
            {t("export")}
          </button>
        }
      />

      <div className="mt-2 mb-6">
        <LiveStrip />
      </div>

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

      <section className="overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_0_rgba(15,23,42,0.03),0_10px_30px_-22px_rgba(15,23,42,0.18)]">
        {main.isLoading ? (
          <SkeletonRows />
        ) : main.isError ? (
          <ErrorBlock
            message={
              main.error instanceof Error
                ? main.error.message
                : t("load_error")
            }
          />
        ) : visibleItems.length === 0 ? (
          apiHasZero ? <EmptyZero /> : <EmptyFiltered />
        ) : (
          <Table
            items={visibleItems}
            isStale={main.isFetching}
            onRowClick={(id) => router.push(`/dossier/${id}`)}
          />
        )}

        {main.data && main.data.total > 0 && totalPages > 1 ? (
          <Pagination
            page={page}
            totalPages={totalPages}
            shownCount={visibleItems.length}
            apiTotal={main.data.total}
            onSetPage={setPage}
          />
        ) : main.data && main.data.total > 0 ? (
          <PaginationFooter
            shownCount={visibleItems.length}
            apiTotal={main.data.total}
          />
        ) : null}
      </section>
      </div>
    </>
  );
}

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
  const t = useTranslations("bank.history");
  const items: Array<{ key: ListFilter; label: string; count: number | null }> =
    [
      { key: "mine", label: t("tab_mine"), count: mineCount },
      { key: "all", label: t("tab_all"), count: allCount },
    ];
  return (
    <div className="mb-5 inline-flex gap-0 rounded-lg bg-[var(--surface-3)] p-[3px]">
      {items.map((it) => {
        const active = value === it.key;
        return (
          <button
            key={it.key}
            type="button"
            onClick={() => onChange(it.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-[13.5px] font-medium transition-colors",
              active
                ? "bg-[var(--surface)] text-[var(--ink-1)] shadow-[0_1px_1px_rgba(15,23,42,0.04)]"
                : "text-[var(--ink-3)] hover:text-[var(--ink-1)]",
            )}
          >
            {it.label}
            {it.count != null ? (
              <span
                className={cn(
                  "rounded-full px-1.5 py-px text-[11px]",
                  active
                    ? "bg-[var(--surface-2)] text-[var(--ink-3)]"
                    : "bg-[var(--surface-2)] text-[var(--ink-3)]",
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
  const t = useTranslations("bank.history");
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
      <form onSubmit={onSubmit} className="flex-1" style={{ maxWidth: 460 }}>
        <div className="relative flex items-center">
          <Search className="pointer-events-none absolute left-3 size-4 text-[var(--ink-4)]" />
          <input
            type="search"
            placeholder={t("search_placeholder")}
            value={q}
            onChange={(e) => onQ(e.target.value)}
            className="h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-9 text-[13.5px] text-[var(--ink-1)] outline-none transition-colors placeholder:text-[var(--ink-4)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_4px_var(--brand-primary-ring)]"
          />
          {q ? (
            <button
              type="button"
              onClick={() => onQ("")}
              aria-label={t("clear_aria")}
              className="absolute right-2 grid size-[22px] place-items-center rounded text-[var(--ink-4)] hover:bg-[var(--surface-2)] hover:text-[var(--ink-2)]"
            >
              <X className="size-3.5" />
            </button>
          ) : null}
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect
          label={t("filter_recommendation")}
          value={recFilter}
          onChange={(v) => onRecFilter(v as RecFilter)}
          options={[
            { v: "all", l: t("rec_all") },
            { v: "approve", l: t("rec_approve") },
            { v: "review", l: t("rec_review") },
            { v: "reject", l: t("rec_reject") },
          ]}
        />
        <FilterSelect
          label={t("filter_period")}
          value={dateFilter}
          onChange={(v) => onDateFilter(v as DateFilter)}
          options={[
            { v: "7", l: t("period_7") },
            { v: "30", l: t("period_30") },
            { v: "90", l: t("period_90") },
            { v: "all", l: t("period_all") },
          ]}
        />
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
    <label className="relative inline-flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 text-[13px] text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--ink-1)]">
      <span className="text-[12px] text-[var(--ink-3)]">{label}:</span>
      <span className="text-[var(--ink-1)]">{current?.l ?? ""}</span>
      <ChevronDown className="size-3.5 text-[var(--ink-4)]" />
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
      <table className="w-full border-collapse text-[13.5px]">
        <thead className="sticky top-0 z-[1]">
          <tr>
            <TableHeaders />
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

function TableHeaders() {
  const t = useTranslations("bank.history");
  return (
    <>
      <Th width={140}>{t("col_inn")}</Th>
      <Th>{t("col_company")}</Th>
      <Th width={140}>{t("col_score")}</Th>
      <Th width={160}>{t("col_recommendation")}</Th>
      <Th width={200}>{t("col_date")}</Th>
      <Th width={180}>{t("col_analyst")}</Th>
      <Th width={32} />
    </>
  );
}

function Th({ children, width }: { children?: React.ReactNode; width?: number }) {
  return (
    <th
      style={width ? { width } : undefined}
      className="bg-[var(--surface)] px-[18px] pt-3.5 pb-3 text-left text-[10.5px] font-medium tracking-[0.08em] whitespace-nowrap text-[var(--ink-4)] uppercase shadow-[inset_0_-1px_0_var(--border)]"
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
      className="group cursor-pointer border-b border-[var(--border)] transition-colors last:border-b-0 hover:bg-[var(--surface-2)]"
    >
      <td className="px-[18px] py-3.5 font-mono text-[12.5px] tabular-nums text-[var(--ink-2)]">
        {item.borrower_inn_masked}
      </td>
      <td className="px-[18px] py-3.5 font-semibold text-[var(--ink-1)]">
        {item.borrower_name}
      </td>
      <td className="px-[18px] py-3.5">
        <ScoreCell score={item.display_score} rec={item.recommendation} />
      </td>
      <td className="px-[18px] py-3.5">
        <RecBadge rec={item.recommendation} />
      </td>
      <td className="px-[18px] py-3.5">
        <DateCell iso={item.created_at} />
      </td>
      <td className="px-[18px] py-3.5">
        <AnalystCell name={item.analyst_full_name} />
      </td>
      <td className="px-[18px] py-3.5">
        <ChevronRight
          className="size-3.5 -translate-x-1 text-[var(--brand-primary)] opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100"
          aria-hidden
        />
      </td>
    </tr>
  );
}

function ScoreCell({
  score,
  rec,
}: {
  score: number;
  rec: BankDossierListItem["recommendation"];
}) {
  // Цвет акцент-полоски — по recommendation (как ScoreRing в /search).
  // Число тоном — по score band (отдельная семантика «качество vs решение»).
  const recBand = recommendationBand(rec);
  const numBand: ScoreTone = scoreBand(score) ?? "warn";
  const stripColor: Record<"good" | "warn" | "bad", string> = {
    good: "var(--state-ok-fg)",
    warn: "var(--state-warn-fg)",
    bad: "var(--state-bad-fg)",
  };
  const numColor: Record<ScoreTone, string> = {
    good: "var(--state-ok-fg)",
    warn: "var(--state-warn-fg)",
    bad: "var(--state-bad-fg)",
  };
  return (
    <span className="inline-flex items-center gap-2.5">
      <span
        aria-hidden
        className="block h-[22px] w-[3px] rounded-[3px]"
        style={{ background: stripColor[recBand] }}
      />
      <span
        className="font-mono text-[16px] font-semibold tabular-nums"
        style={{ color: numColor[numBand], letterSpacing: "-0.01em" }}
      >
        {score}
      </span>
    </span>
  );
}

function RecBadge({ rec }: { rec: BankDossierListItem["recommendation"] }) {
  const t = useTranslations("bank.history");
  const band = recommendationBand(rec);
  const colors: Record<"good" | "warn" | "bad", { fg: string; bg: string }> = {
    good: { fg: "var(--state-ok-fg)", bg: "var(--state-ok-bg)" },
    warn: { fg: "var(--state-warn-fg)", bg: "var(--state-warn-bg)" },
    bad: { fg: "var(--state-bad-fg)", bg: "var(--state-bad-bg)" },
  };
  const c = colors[band];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12.5px] font-medium whitespace-nowrap"
      style={{ color: c.fg, background: c.bg }}
    >
      <span
        className="size-1.5 rounded-full"
        style={{ background: c.fg }}
        aria-hidden
      />
      {t(`rec_${rec}`)}
    </span>
  );
}

function DateCell({ iso }: { iso: string }) {
  const t = useTranslations("bank.history");
  const rel = formatRelativeTime(iso);
  const fresh = isFreshTime(iso);
  let relText: string | null = null;
  if (rel) {
    if (rel.key === "rel_just_now") {
      relText = t("rel_just_now");
    } else if (rel.key === "rel_yesterday") {
      relText = t("rel_yesterday", rel.values);
    } else {
      relText = t(rel.key, rel.values);
    }
  }
  return (
    <span className="flex flex-col leading-tight">
      <span className="text-[13px] text-[var(--ink-2)]">
        {formatRuDate(iso)}
      </span>
      {relText ? (
        <span
          className={cn(
            "mt-0.5 text-[11px]",
            fresh
              ? "font-medium text-[var(--state-ok-fg)]"
              : "text-[var(--ink-4)]",
          )}
        >
          {relText}
        </span>
      ) : null}
    </span>
  );
}

function AnalystCell({ name }: { name: string | null }) {
  if (!name) {
    return <span className="text-[12px] text-[var(--ink-4)]">—</span>;
  }
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="grid size-[24px] shrink-0 place-items-center rounded-full text-[10px] font-bold text-white"
        style={{
          background:
            "linear-gradient(135deg, var(--brand-primary-soft) 0%, var(--brand-primary) 100%)",
        }}
      >
        {initials(name)}
      </span>
      <span className="text-[12.5px] text-[var(--ink-1)]">{name}</span>
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
  const t = useTranslations("bank.history");
  const pages = pageNumbers(page, totalPages);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-[12.5px] text-[var(--ink-3)]">
      <span>
        {t.rich("pagination_shown", {
          shown: shownCount,
          total: apiTotal,
          b: (chunks) => (
            <b className="font-mono font-semibold tabular-nums text-[var(--ink-1)]">
              {chunks}
            </b>
          ),
        })}
      </span>
      <div className="flex items-center gap-1">
        <PageBtn
          disabled={page <= 1}
          onClick={() => onSetPage(page - 1)}
          aria-label={t("pagination_prev")}
        >
          <ChevronLeft className="size-3.5" />
        </PageBtn>
        {pages.map((p, i) =>
          p === "gap" ? (
            <span key={`gap-${i}`} className="px-1.5 text-[var(--ink-4)]">
              …
            </span>
          ) : (
            <PageBtn key={p} active={p === page} onClick={() => onSetPage(p)}>
              {p}
            </PageBtn>
          ),
        )}
        <PageBtn
          disabled={page >= totalPages}
          onClick={() => onSetPage(page + 1)}
          aria-label={t("pagination_next")}
        >
          <ChevronRight className="size-3.5" />
        </PageBtn>
      </div>
    </div>
  );
}

function PaginationFooter({
  shownCount,
  apiTotal,
}: {
  shownCount: number;
  apiTotal: number;
}) {
  const t = useTranslations("bank.history");
  return (
    <div className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-[12.5px] text-[var(--ink-3)]">
      {t.rich("pagination_shown", {
        shown: shownCount,
        total: apiTotal,
        b: (chunks) => (
          <b className="font-mono font-semibold tabular-nums text-[var(--ink-1)]">
            {chunks}
          </b>
        ),
      })}
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
        "inline-flex h-7 min-w-[28px] items-center justify-center rounded-md px-2 font-mono text-[12.5px] font-semibold tabular-nums transition-colors",
        active
          ? "bg-[var(--ink-1)] text-white hover:bg-[var(--ink-1)]"
          : "bg-transparent text-[var(--ink-2)] hover:bg-[var(--surface-3)] hover:text-[var(--ink-1)]",
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
          className="h-10 animate-pulse rounded-md bg-[var(--surface-2)]"
        />
      ))}
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  const t = useTranslations("bank.history");
  return (
    <div className="px-5 py-10 text-center text-[13px] text-[var(--state-bad-fg)]">
      {t("load_error")}: {message}
    </div>
  );
}

function EmptyFiltered() {
  const t = useTranslations("bank.history");
  return (
    <EmptyState
      title={t("empty_title")}
      desc={t("empty_desc")}
      icon={<Search className="size-7" />}
    />
  );
}

function EmptyZero() {
  const t = useTranslations("bank.history");
  return (
    <EmptyState
      title={t("empty_zero_title")}
      desc={t("empty_zero_desc")}
      icon={<FileSearch className="size-7" />}
    />
  );
}

function EmptyState({
  title,
  desc,
  icon,
}: {
  title: string;
  desc: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="px-6 py-16 text-center">
      <div className="relative mx-auto mb-5 size-[72px]">
        <div
          aria-hidden
          className="absolute -inset-9 opacity-70"
          style={{
            background:
              "radial-gradient(circle, var(--brand-primary-soft) 0%, transparent 70%)",
          }}
        />
        <div
          className="relative grid size-full place-items-center rounded-2xl border border-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]"
          style={{
            background:
              "linear-gradient(180deg, var(--surface) 0%, var(--brand-primary-soft) 100%)",
          }}
        >
          {icon}
        </div>
      </div>
      <div className="text-[16px] font-semibold text-[var(--ink-1)]">
        {title}
      </div>
      <div className="mx-auto mt-1.5 max-w-[380px] text-[13px] leading-[1.5] text-[var(--ink-3)]">
        {desc}
      </div>
    </div>
  );
}
