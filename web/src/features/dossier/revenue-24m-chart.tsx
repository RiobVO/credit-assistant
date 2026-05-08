"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SectionCard } from "@/components/section-card";
import type { DossierViewDto } from "@/lib/api";

import { formatBigUzs, formatMonthShort } from "./format";

const PERIODS = [
  { value: 24, key: "period_24" as const },
  { value: 12, key: "period_12" as const },
  { value: 6, key: "period_6" as const },
];

type Period = (typeof PERIODS)[number]["value"];

export function Revenue24mChart({
  data,
  hasAnnualRevenue,
}: {
  data: DossierViewDto["monthly_revenue_24m"];
  hasAnnualRevenue: boolean;
}) {
  const t = useTranslations("dossier.revenue_chart");
  const [period, setPeriod] = useState<Period>(24);

  // Backend отдаёт Decimal как str — парсим один раз. Recharts работает
  // с числами, формат UZS до тыс. достаточно.
  const numericData = data.map((p) => ({
    month: p.month,
    revenue: parseFloat(p.revenue),
    trend: parseFloat(p.trend),
    is_peak: p.is_peak,
  }));
  const slice = numericData.slice(-period);

  if (slice.length === 0) {
    return <EmptyChart hasAnnualRevenue={hasAnnualRevenue} />;
  }

  const peakIndex = slice.reduce(
    (best, p, i) => (p.revenue > slice[best].revenue ? i : best),
    0,
  );
  const peakLabel = formatMonthShort(slice[peakIndex].month);

  const periodSelector = (
    <div className="inline-flex rounded-md border border-[var(--border)] bg-[var(--surface)] p-0.5">
      {PERIODS.map((p) => (
        <button
          key={p.value}
          type="button"
          onClick={() => setPeriod(p.value)}
          className={`px-2.5 py-1 text-[12px] font-medium transition-colors ${
            period === p.value
              ? "rounded-[5px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-hover)]"
              : "text-[var(--ink-3)] hover:text-[var(--ink-2)]"
          }`}
        >
          {t(p.key)}
        </button>
      ))}
    </div>
  );

  return (
    <SectionCard
      title={t("title", { months: period })}
      sub={t("subtitle", { peak: peakLabel })}
      aux={periodSelector}
    >
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={slice}
            margin={{ top: 8, right: 14, bottom: 0, left: 8 }}
          >
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis
              dataKey="month"
              tickFormatter={formatMonthShort}
              tick={{ fontSize: 11, fill: "var(--ink-4)" }}
              axisLine={{ stroke: "var(--border)" }}
              tickLine={false}
              interval={Math.max(0, Math.floor(slice.length / 12) - 1)}
            />
            <YAxis
              tickFormatter={(v: number) => `${(v / 1_000_000_000).toFixed(1)}`}
              tick={{ fontSize: 11, fill: "var(--ink-4)" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              cursor={{ fill: "var(--surface-2)" }}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--border)",
                fontSize: 12,
              }}
              labelFormatter={(label) =>
                typeof label === "string" ? formatMonthShort(label) : String(label)
              }
              formatter={(value, name) => {
                const num = typeof value === "number" ? value : Number(value);
                const label =
                  name === "revenue" ? t("tooltip_revenue") : t("tooltip_trend");
                return [formatBigUzs(num), label];
              }}
            />
            <Bar dataKey="revenue" barSize={Math.min(22, 600 / slice.length)}>
              {slice.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    entry.is_peak ? "var(--chart-orange)" : "var(--chart-grey)"
                  }
                />
              ))}
            </Bar>
            <Line
              type="monotone"
              dataKey="trend"
              stroke="var(--chart-blue)"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex items-center gap-4 px-2 text-[11.5px] text-[var(--ink-3)]">
        <Legend color="var(--chart-grey)" label={t("legend_monthly")} />
        <Legend color="var(--chart-orange)" label={t("legend_peak")} />
        <Legend color="var(--chart-blue)" label={t("legend_trend")} />
      </div>
    </SectionCard>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="size-2.5 rounded-[3px]"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

// CA-036: два сценария empty state различает аналитик с одного взгляда.
// hasAnnualRevenue = true  → годовые данные посчитаны из FORM_2, нет лишь
//                            помесячной разбивки (нужен ESF CSV — CA-032).
// hasAnnualRevenue = false → INSUFFICIENT: вообще нет ни годовой, ни помесячной.
function EmptyChart({ hasAnnualRevenue }: { hasAnnualRevenue: boolean }) {
  const t = useTranslations("dossier.revenue_chart");
  const title = hasAnnualRevenue
    ? t("empty_title_has_annual")
    : t("empty_title_no_data");
  const subtitle = hasAnnualRevenue
    ? t("empty_subtitle_has_annual")
    : t("empty_subtitle_no_data");
  const body = hasAnnualRevenue
    ? t("empty_body_has_annual")
    : t("empty_body_no_data");

  return (
    <SectionCard title={title} sub={subtitle}>
      <div className="flex h-[160px] items-center justify-center px-2 text-center text-[13px] text-[var(--ink-3)]">
        {body}
      </div>
    </SectionCard>
  );
}
