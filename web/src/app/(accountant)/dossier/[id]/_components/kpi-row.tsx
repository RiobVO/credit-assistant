import type { DossierViewDto } from "@/lib/api";

import { formatBigUzs, formatPct, formatRatio } from "../_lib/format";

import { KpiCard } from "./kpi-card";

export function KpiRow({ kpis }: { kpis: DossierViewDto["kpis"] }) {
  // Для revenue/EBITDA рост YoY = positive; для Debt/EBITDA рост = negative
  // (увеличение долговой нагрузки — ухудшение).
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        label="Выручка LTM"
        value={formatBigUzs(kpis.revenue_ltm.value)}
        yoyPct={kpis.revenue_ltm.yoy_pct}
        changeTone={kpis.revenue_ltm.yoy_pct >= 0 ? "positive" : "negative"}
        sparkline={kpis.revenue_ltm.sparkline}
      />
      <KpiCard
        label="EBITDA"
        value={formatBigUzs(kpis.ebitda.value)}
        yoyPct={kpis.ebitda.yoy_pct}
        changeTone={kpis.ebitda.yoy_pct >= 0 ? "positive" : "negative"}
        sparkline={kpis.ebitda.sparkline}
      />
      <KpiCard
        label="ROE"
        value={formatPct(kpis.roe.value)}
        yoyPct={kpis.roe.yoy_pct}
        changeTone={kpis.roe.yoy_pct >= 0 ? "positive" : "negative"}
        sparkline={kpis.roe.sparkline}
      />
      <KpiCard
        label="Долг / EBITDA"
        value={formatRatio(kpis.debt_to_ebitda.value)}
        yoyPct={kpis.debt_to_ebitda.yoy_pct}
        changeTone={kpis.debt_to_ebitda.yoy_pct <= 0 ? "positive" : "negative"}
        sparkline={kpis.debt_to_ebitda.sparkline}
      />
    </div>
  );
}
