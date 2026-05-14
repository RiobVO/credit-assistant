"use client";

// DSCR pre-score: ежемесячный платёж (аннуитет) + Debt/Revenue + DSCR gauge с
// классификацией риска. Read-only preview данных Шага 2 + Шага 3.
//
// Phase 8 design statement:
//   • Section card pattern (Phase 6/7/8) — TrendingUp icon + static «обновлено»
//   • Pulse-dot убран (TODO[CA-DS19] motion-cleanup в банке)
//   • Sparkbars убраны (decoration без real-data binding)
//   • Hex sweep на semantic state-{ok,warn,bad}-{bg,border,fg}
//
// CA-033: annualRevenue / annualNetProfit nullable — null = «нет данных от
// Шага 2» (neutral pill «Недостаточно данных»), число = классифицируем риск.

import { format } from "date-fns";
import { TrendingUp } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  classifyDscrRisk,
  computeAnnuityMonthly,
  computeDebtToRevenuePct,
  computeDscr,
  computeOverpayment,
  formatUzs,
} from "../lib/finance";

import { DscrGauge } from "./dscr-gauge";
import { SectionCard, StaticPill } from "./section-card";

type Props = {
  loanAmount: number;
  termMonths: number;
  ratePct: number;
  // CA-033: nullable — null = «нет данных от Шага 2» (neutral pill),
  // число (включая 0/отрицательные) = есть данные, классифицируем риск.
  annualRevenue: number | null;
  annualNetProfit: number | null;
};

export function DscrSummary({
  loanAmount,
  termMonths,
  ratePct,
  annualRevenue,
  annualNetProfit,
}: Props) {
  const t = useTranslations("accountant.manual_input");
  const monthly = computeAnnuityMonthly(loanAmount, ratePct, termMonths);
  const overpayment = computeOverpayment(monthly, termMonths, loanAmount);
  const dscr = computeDscr(annualNetProfit, monthly);
  const debtToRevenue = computeDebtToRevenuePct(loanAmount, annualRevenue);
  const overpaymentPct =
    loanAmount > 0 ? (overpayment / loanAmount) * 100 : 0;
  const risk = classifyDscrRisk(dscr);

  const todayLabel = format(new Date(), "dd.MM.yyyy");

  return (
    <SectionCard
      icon={<TrendingUp className="size-[18px]" />}
      title={
        <span className="flex items-center gap-2">
          {t("s3_calc_heading")}
          <span className="text-[12px] font-medium text-[var(--ink-4)]">
            {t("dscr_pre_score_eyebrow")}
          </span>
        </span>
      }
      sub={t("s3_calc_sub")}
      aux={
        <StaticPill>
          {t("dscr_static_updated", { date: todayLabel })}
        </StaticPill>
      }
    >
      {/* Inner grid: 230px gauge column + 1fr metrics. Расширяем на всю ширину
          body, отменяя -22px section-body padding через -m. */}
      <div className="-m-[22px] grid grid-cols-1 md:grid-cols-[230px_1fr]">
        <div className="flex flex-col items-center gap-[14px] border-r border-[var(--border)] bg-gradient-to-b from-[var(--surface-2)] to-white px-[22px] py-6">
          <DscrGauge value={dscr} />
          <RiskChip tone={risk.tone}>{t(risk.key)}</RiskChip>
          <div className="font-mono text-[11px] text-[var(--ink-4)]">
            {dscr == null
              ? t("dscr_no_data")
              : t("dscr_norm", { pct: (dscr * 100).toFixed(0) })}
          </div>
        </div>

        <div className="flex flex-col justify-center gap-[18px] px-[26px] py-[22px]">
          <div className="flex items-end justify-between gap-[18px] border-b border-dashed border-[var(--border)] pb-[18px]">
            <div>
              <div className="mb-2 text-[11px] font-medium tracking-[0.07em] text-[var(--ink-4)] uppercase">
                {t("dscr_monthly_label")}
              </div>
              <div className="font-mono text-[34px] leading-none font-semibold tracking-[-0.03em] text-[var(--ink-1)]">
                {monthly > 0 ? formatUzs(String(monthly)) : "—"}
                {monthly > 0 ? (
                  <span className="ml-1.5 text-[14px] font-medium tracking-[0.04em] text-[var(--ink-4)]">
                    UZS
                  </span>
                ) : null}
              </div>
              <div className="mt-2 font-mono text-[11.5px] text-[var(--ink-3)]">
                {t("dscr_monthly_hint", {
                  months: termMonths,
                  rate: ratePct.toString().replace(".", ","),
                })}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-[1fr_1px_1fr_1px_1fr] items-center">
            <SecondaryMetric
              label={t("dscr_loan_label")}
              value={loanAmount > 0 ? formatUzs(String(loanAmount)) : "—"}
              unit={loanAmount > 0 ? "UZS" : undefined}
              hint={t("dscr_loan_hint", { months: termMonths })}
            />
            <span className="h-9 w-px bg-[var(--border)]" />
            <SecondaryMetric
              label={t("dscr_overpay_label")}
              value={overpayment > 0 ? formatUzs(String(overpayment)) : "—"}
              unit={overpayment > 0 ? "UZS" : undefined}
              hint={
                <>
                  <span className="font-mono font-semibold text-[var(--state-ok-fg)]">
                    {overpaymentPct.toFixed(1).replace(".", ",")}%
                  </span>{" "}
                  {t("dscr_overpay_hint_suffix")}
                </>
              }
            />
            <span className="h-9 w-px bg-[var(--border)]" />
            <SecondaryMetric
              label={t("dscr_dr_label")}
              value={
                debtToRevenue != null
                  ? debtToRevenue.toFixed(1).replace(".", ",")
                  : "—"
              }
              unit={debtToRevenue != null ? "%" : undefined}
              hint={t("dscr_dr_hint")}
            />
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

function RiskChip({
  tone,
  children,
}: {
  tone: "success" | "warning" | "danger" | "neutral";
  children: React.ReactNode;
}) {
  // CA-033: neutral для «нет данных» — серая палитра surface-2, не путать
  // с warning amber.
  const palette = {
    success:
      "bg-[var(--state-ok-bg)] border-[var(--state-ok-border)] text-[var(--state-ok-fg)]",
    warning:
      "bg-[var(--state-warn-bg)] border-[var(--state-warn-border)] text-[var(--state-warn-fg)]",
    danger:
      "bg-[var(--state-bad-bg)] border-[var(--state-bad-border)] text-[var(--state-bad-fg)]",
    neutral: "bg-[var(--surface-2)] border-[var(--border-strong)] text-[var(--ink-3)]",
  }[tone];
  const dot = {
    success: "bg-[var(--state-ok-fg)]",
    warning: "bg-[var(--state-warn-fg)]",
    danger: "bg-[var(--state-bad-fg)]",
    neutral: "bg-[var(--ink-4)]",
  }[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-[10px] py-[5px] text-[11.5px] font-semibold ${palette}`}
    >
      <span className={`size-1.5 rounded-full ${dot}`} />
      {children}
    </span>
  );
}

function SecondaryMetric({
  label,
  value,
  unit,
  hint,
}: {
  label: string;
  value: string;
  unit?: string;
  hint: React.ReactNode;
}) {
  return (
    <div className="px-1">
      <div className="mb-1.5 text-[10.5px] font-medium tracking-[0.06em] text-[var(--ink-4)] uppercase">
        {label}
      </div>
      <div className="flex items-baseline gap-1.5 font-mono text-[17px] font-semibold tracking-[-0.02em] text-[var(--ink-1)]">
        {value}
        {unit ? (
          <span className="text-[11px] font-medium text-[var(--ink-4)]">
            {unit}
          </span>
        ) : null}
      </div>
      <div className="mt-1 flex items-center gap-1 text-[11px] text-[var(--ink-4)]">
        {hint}
      </div>
    </div>
  );
}
