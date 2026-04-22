import type { DossierViewDto, KpiValueDto } from "@/lib/api";

import { formatBigUzs, formatPct, formatRatio } from "./format";

import { KpiCard } from "./kpi-card";

type Format = "uzs" | "pct" | "ratio";
type GrowthDirection = "up_is_good" | "down_is_good";

export function KpiRow({ kpis }: { kpis: DossierViewDto["kpis"] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiSlot label="Выручка LTM" kpi={kpis.revenue_ltm} format="uzs" growth="up_is_good" />
      <KpiSlot label="EBITDA" kpi={kpis.ebitda} format="uzs" growth="up_is_good" />
      <KpiSlot label="ROE" kpi={kpis.roe} format="pct" growth="up_is_good" />
      <KpiSlot
        label="Долг / EBITDA"
        kpi={kpis.debt_to_ebitda}
        format="ratio"
        growth="down_is_good"
      />
    </div>
  );
}

function KpiSlot({
  label,
  kpi,
  format,
  growth,
}: {
  label: string;
  kpi: KpiValueDto | null;
  format: Format;
  growth: GrowthDirection;
}) {
  if (kpi === null) {
    return <EmptyKpiCard label={label} />;
  }

  const value = parseFloat(kpi.value);
  const yoyNum = kpi.yoy_pct !== null ? parseFloat(kpi.yoy_pct) : null;
  const sparkline = kpi.sparkline.map((p) => parseFloat(p));

  const isGood =
    yoyNum === null
      ? true
      : growth === "up_is_good"
        ? yoyNum >= 0
        : yoyNum <= 0;

  return (
    <KpiCard
      label={label}
      value={formatValue(value, format)}
      yoyPct={yoyNum}
      changeTone={isGood ? "positive" : "negative"}
      sparkline={sparkline}
    />
  );
}

function EmptyKpiCard({ label }: { label: string }) {
  return (
    <div
      className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]"
      title="Недостаточно данных для расчёта"
    >
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-ink-400)] uppercase">
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ca-ink-400)]">
        —
      </div>
      <div className="mt-2 text-[11.5px] text-[var(--ca-ink-500)]">
        Нет данных для расчёта
      </div>
      <div className="mt-3 h-[36px]" aria-hidden="true" />
    </div>
  );
}

function formatValue(value: number, format: Format): string {
  switch (format) {
    case "uzs":
      return formatBigUzs(value);
    case "pct":
      return formatPct(value);
    case "ratio":
      return formatRatio(value);
  }
}
