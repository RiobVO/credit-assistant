"use client";

import { format } from "date-fns";
import { Clock } from "lucide-react";
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
    <div className="mt-[22px] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="flex items-center gap-2.5 border-b border-[#EFF1F5] bg-[var(--surface)] px-[22px] py-3.5">
        <span className="text-[10.5px] font-semibold tracking-[1.4px] text-[var(--ink-4)] uppercase">
          {t("dscr_pre_score")}
        </span>
        <span className="h-3.5 w-px bg-[var(--border)]" />
        <span className="text-[14px] font-semibold tracking-[-0.1px] text-[var(--ink-1)]">
          {t("dscr_summary_title")}
        </span>
        <div className="ml-auto flex items-center gap-3.5 font-mono text-[12px] text-[var(--ink-3)]">
          <span className="inline-flex items-center gap-1.5 text-[var(--state-ok-fg)]">
            <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)] shadow-[0_0_0_3px_rgba(15,138,95,0.15)]" />
            {t("dscr_updated")}
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="size-3" />
            {t("dscr_annuity_today", { date: todayLabel })}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[230px_1fr]">
        <div className="flex flex-col items-center gap-3.5 border-r border-[#EFF1F5] bg-gradient-to-b from-[#FAFBFC] to-white px-[22px] py-6">
          <DscrGauge value={dscr} />
          <div>
            <RiskChip tone={risk.tone}>{t(risk.key)}</RiskChip>
          </div>
          <div className="font-mono text-[11px] text-[var(--ink-4)]">
            {dscr == null
              ? t("dscr_no_data")
              : t("dscr_norm", { pct: (dscr * 100).toFixed(0) })}
          </div>
        </div>

        <div className="flex flex-col justify-center gap-[18px] px-[26px] py-[22px]">
          <div className="flex items-end justify-between gap-[18px] border-b border-dashed border-[var(--border)] pb-[18px]">
            <div>
              <div className="mb-2 text-[11px] font-medium tracking-[0.7px] text-[var(--ink-4)] uppercase">
                {t("dscr_monthly_label")}
              </div>
              <div className="font-mono text-[34px] leading-none font-semibold tracking-[-1px] text-[var(--ink-1)]">
                {monthly > 0 ? formatUzs(String(monthly)) : "—"}
                {monthly > 0 ? (
                  <span className="ml-1.5 text-[14px] font-medium tracking-[0.4px] text-[var(--ink-4)]">
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
            <Sparkbars />
          </div>

          <div className="grid grid-cols-[1fr_1px_1fr_1px_1fr] items-center">
            <SecondaryMetric
              label={t("dscr_loan_label")}
              value={loanAmount > 0 ? formatUzs(String(loanAmount)) : "—"}
              unit={loanAmount > 0 ? "UZS" : undefined}
              hint={t("dscr_loan_hint", { months: termMonths })}
            />
            <span className="h-9 w-px bg-[#EFF1F5]" />
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
            <span className="h-9 w-px bg-[#EFF1F5]" />
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
    </div>
  );
}

function RiskChip({
  tone,
  children,
}: {
  tone: "success" | "warning" | "danger" | "neutral";
  children: React.ReactNode;
}) {
  const palette = {
    success: "bg-[var(--state-ok-bg)] border-[#BFE2D2] text-[var(--state-ok-fg)]",
    warning: "bg-[#FFF6E5] border-[#F1D9A6] text-[var(--state-warn-fg)]",
    danger: "bg-[#FCE7E5] border-[#F2BCBA] text-[var(--state-bad-fg)]",
    // CA-033: нейтральный «нет данных» — серая палитра, не путать с warning.
    neutral: "bg-[#F1F4F8] border-[#D4D9E0] text-[var(--ink-3)]",
  }[tone];
  const dot = {
    success: "bg-[var(--state-ok-fg)]",
    warning: "bg-[var(--state-warn-fg)]",
    danger: "bg-[var(--state-bad-fg)]",
    neutral: "bg-[var(--ink-4)]",
  }[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[5px] text-[11.5px] font-semibold ${palette}`}
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
      <div className="mb-1.5 text-[10.5px] font-medium tracking-[0.6px] text-[var(--ink-4)] uppercase">
        {label}
      </div>
      <div className="flex items-baseline gap-1.5 font-mono text-[17px] font-semibold tracking-[-0.2px] text-[var(--ink-1)]">
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

function Sparkbars() {
  const heights = [32, 46, 40, 58, 52, 70, 62, 84, 92, 100];
  return (
    <div
      aria-hidden
      className="flex h-12 items-end gap-[3px]"
    >
      {heights.map((h, i) => (
        <span
          key={i}
          className={`block w-1.5 rounded-sm ${
            i >= 7
              ? "bg-gradient-to-b from-[#2459B5] to-[var(--brand-primary)]"
              : "bg-[#D6DEEC]"
          }`}
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}
