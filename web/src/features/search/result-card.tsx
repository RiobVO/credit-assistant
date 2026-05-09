"use client";

import { ArrowRight, Building, ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";

import type { BorrowerSearchResult, SearchCardData } from "@/lib/bank-api";

import { formatRevenueMillions, formatRevenueShort, formatYoy, parseIsoMonth, splitBusinessAge } from "./format";
import { RevenueSparkline, type SparklinePoint } from "./revenue-sparkline";
import { ScoreRing, type Recommendation } from "./score-ring";

// Phase 2 (DS-PHASE-2): ResultCard собирает hero-карточку результата поиска —
// ScoreRing + mini-meta (4 KPI) + RevenueSparkline + 2 CTA. Данные приходят
// одним запросом из `searchBorrower(inn)` через `result.card`.

function formatInn(inn: string): string {
  if (inn.length === 9) {
    return inn.replace(/(\d{3})(\d{3})(\d{3})/, "$1 $2 $3");
  }
  return inn;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export function ResultCard({
  result,
  inn,
  card,
}: {
  result: BorrowerSearchResult;
  inn: string;
  card: SearchCardData;
}) {
  const t = useTranslations("bank.search");

  const revenue = formatRevenueShort(card.revenue_ltm);
  const yoy = card.yoy_pct != null ? formatYoy(card.yoy_pct) : null;
  const age = card.business_age_months != null ? splitBusinessAge(card.business_age_months) : null;
  const ageLabel = age
    ? t("business_age_template", { years: age.years, months: age.months }).trim()
    : null;

  const points: SparklinePoint[] = card.monthly_revenue_12m.map((p) => ({
    month: p.month,
    revenue: p.revenue,
  }));

  const fmtTooltip = (p: SparklinePoint): string => {
    const parsed = parseIsoMonth(p.month);
    if (!parsed) return p.month;
    const monthShort = t(`month_short_${parsed.monthIndex}`);
    return t("spark_value_format", {
      month: `${monthShort} ${parsed.yearShort}`,
      value: formatRevenueMillions(p.revenue),
    });
  };

  return (
    <div className="relative overflow-hidden rounded-[16px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_0_rgba(255,255,255,0.8)_inset,0_1px_2px_rgba(14,21,37,0.03),0_14px_32px_-22px_rgba(14,21,37,0.12)] animate-[rise-card_0.65s_cubic-bezier(0.16,0.84,0.44,1)_both]">
      {/* Subtle brand-tinted radial accent в углу — premium card depth. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(640px 200px at 88% 0%, color-mix(in oklab, var(--brand-primary) 5%, transparent) 0%, transparent 70%)",
        }}
      />
      <div className="relative grid gap-7 p-7 pb-5 md:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-[10px] text-[12px] text-[var(--ink-3)]">
            <Building className="size-[14px]" />
            <span className="font-mono text-[var(--ink-2)]">{formatInn(inn)}</span>
            <span className="text-[var(--border-strong)]">·</span>
            <span
              className="inline-flex items-center gap-[6px] rounded-full border px-2.5 py-[3px] text-[11px] font-semibold"
              style={{
                background: "var(--state-ok-bg)",
                color: "var(--state-ok-fg)",
                borderColor: "var(--state-ok-border)",
              }}
            >
              {/* CA-DS19: pulse убран — banking tone требует static индикаторы. */}
              <span
                aria-hidden
                className="size-1.5 rounded-full"
                style={{ background: "var(--state-ok-fg)" }}
              />
              {t("found_pill")}
            </span>
          </div>
          <h2 className="m-0 text-[24px] leading-[1.12] font-semibold tracking-[-0.02em] text-[var(--ink-1)]">
            {result.borrower_name ?? "—"}
          </h2>
          {result.created_at ? (
            <p className="mt-1.5 text-[12.5px] text-[var(--ink-3)]">
              {t("found_last_updated")} {fmtDate(result.created_at)}
            </p>
          ) : null}

          {/* Mini-meta — 4 KPI плотным рядом. Все nullable, скрываем при отсутствии. */}
          <div className="mt-5 flex flex-wrap gap-x-6 gap-y-3">
            {revenue ? (
              <MiniStat label={t("mini_revenue_ltm")} value={revenue} />
            ) : null}
            {yoy ? (
              <MiniStat
                label={t("mini_yoy")}
                value={yoy}
                tone={card.yoy_pct != null && card.yoy_pct > 0 ? "good" : card.yoy_pct != null && card.yoy_pct < 0 ? "bad" : null}
              />
            ) : null}
            {ageLabel ? <MiniStat label={t("mini_business_age")} value={ageLabel} /> : null}
            <MiniStat
              label={t("mini_signals")}
              value={t("mini_signals_value", {
                fired: card.signals_total,
                total: card.signals_evaluated,
              })}
            />
          </div>
        </div>

        <div className="border-l border-[var(--border)] pl-7 md:min-w-[180px]">
          <ScoreRing
            displayScore={result.display_score ?? 0}
            recommendation={card.recommendation}
            recommendationLabel={recLabel(t, card.recommendation)}
            label={t("found_scoring_label")}
            denominator={t("found_scoring_denom")}
          />
        </div>
      </div>

      {/* Sparkline strip — revenue · 12 мес + hover tooltip + 2 CTA. */}
      <div
        className="grid items-center gap-5 border-t border-[var(--border)] px-7 py-4 md:grid-cols-[auto_1fr_auto]"
        style={{
          background:
            "linear-gradient(180deg, transparent 0%, var(--surface-2) 100%)",
        }}
      >
        <div className="flex flex-col gap-[2px]">
          <span className="text-[9.5px] font-semibold tracking-[0.1em] text-[var(--ink-4)] uppercase">
            {t("spark_label")}
          </span>
          <span className="font-mono text-[12.5px] font-medium text-[var(--ink-1)]">
            {t("spark_observations", { count: points.length })}
          </span>
        </div>
        <div className="min-w-0">
          {points.length > 0 ? (
            <RevenueSparkline points={points} formatTooltip={fmtTooltip} height={48} />
          ) : (
            <div className="h-[48px]" />
          )}
        </div>
        <div className="flex gap-2">
          {result.dossier_id ? (
            <Link
              href={`/dossier/${result.dossier_id}`}
              className="inline-flex h-9 items-center gap-2 rounded-[9px] border border-[var(--border)] bg-[var(--surface)] px-3 text-[12.5px] font-medium text-[var(--ink-1)] transition-all hover:-translate-y-px hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)]"
            >
              <ExternalLink className="size-[13px]" />
              {t("found_open_dossier")}
            </Link>
          ) : null}
          <Link
            href={`/manual-input?inn=${encodeURIComponent(inn)}`}
            className="inline-flex h-9 items-center gap-2 rounded-[9px] bg-[var(--brand-primary)] px-3.5 text-[12.5px] font-semibold text-white shadow-[0_6px_16px_-8px_color-mix(in_oklab,var(--brand-primary)_55%,transparent)] transition-all hover:-translate-y-px hover:bg-[var(--brand-primary-hover)] hover:shadow-[0_10px_22px_-8px_color-mix(in_oklab,var(--brand-primary)_70%,transparent)]"
          >
            {t("found_rebuild")}
            <ArrowRight className="size-[13px]" />
          </Link>
        </div>
      </div>
    </div>
  );
}

function recLabel(t: (k: string) => string, rec: Recommendation): string {
  if (rec === "approve") return t("recommendation_approve");
  if (rec === "review") return t("recommendation_review");
  return t("recommendation_reject");
}

function MiniStat({
  label,
  value,
  tone = null,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad" | null;
}) {
  const colorClass =
    tone === "good"
      ? "text-[var(--state-ok-fg)]"
      : tone === "bad"
        ? "text-[var(--state-bad-fg)]"
        : "text-[var(--ink-1)]";
  return (
    <div className="flex min-w-0 flex-col gap-[2px]">
      <span className="text-[9.5px] font-semibold tracking-[0.1em] text-[var(--ink-4)] uppercase">
        {label}
      </span>
      <span className={`font-mono text-[13px] font-medium tabular-nums ${colorClass}`}>{value}</span>
    </div>
  );
}
