import type { DossierViewDto, KpiValueDto } from "@/lib/api";

import { formatBigUzs, formatPct, formatRatio } from "./format";

import { KpiCard } from "./kpi-card";

type Format = "uzs" | "pct" | "ratio";
type GrowthDirection = "up_is_good" | "down_is_good";

export function KpiRow({ kpis }: { kpis: DossierViewDto["kpis"] }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiSlot
        label="Выручка LTM"
        kpi={kpis.revenue_ltm}
        format="uzs"
        growth="up_is_good"
      />
      <EbitSlot kpi={kpis.ebit} />
      <RoeSlot kpi={kpis.roe} />
      <DebtToEbitSlot debtToEbit={kpis.debt_to_ebit} ebit={kpis.ebit} />
    </div>
  );
}

// ----------- Generic slot: revenue_ltm and other simple cards ----------------

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
  // == null ловит и undefined (Docker API ещё не пересобран после CA-037 rename
  // → response может прийти без ключей ebit/debt_to_ebit). Без этого слот падает.
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint="Нет данных для расчёта" />;
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

// ----------- CA-037: EBIT slot with tooltip ---------------------------------

function EbitSlot({ kpi }: { kpi: KpiValueDto | null }) {
  // CA-037 контракт: пока depreciation/amortization недоступен, показываем EBIT
  // как прокси EBITDA. Tooltip объясняет honest scoping.
  const label = "EBIT (прокси EBITDA)";
  const tooltip = "D&A недоступен без формы №5 / PROFIT_TAX — показываем EBIT";
  if (kpi == null) {
    return (
      <EmptyKpiCard
        label={label}
        hint="Нужны данные FORM_2 (PBT + проценты)"
        tooltip={tooltip}
      />
    );
  }
  const value = parseFloat(kpi.value);
  const yoy = kpi.yoy_pct !== null ? parseFloat(kpi.yoy_pct) : null;
  return (
    <KpiCard
      label={label}
      value={formatBigUzs(value)}
      yoyPct={yoy}
      changeTone={yoy === null || yoy >= 0 ? "positive" : "negative"}
      sparkline={[]}
      tooltip={tooltip}
    />
  );
}

// ----------- CA-037: ROE slot with reason on null ---------------------------

function RoeSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const label = "ROE";
  if (kpi == null) {
    // Backend возвращает null когда equity_avg ≤ 0 или компоненты отсутствуют.
    // Без отдельного флага frontend не может различить эти две причины — даём
    // составную подсказку, которая корректна в обоих случаях.
    return (
      <EmptyKpiCard
        label={label}
        hint="Нужен собственный капитал из FORM_1 (положительный)"
      />
    );
  }
  const value = parseFloat(kpi.value);
  const yoy = kpi.yoy_pct !== null ? parseFloat(kpi.yoy_pct) : null;
  return (
    <KpiCard
      label={label}
      value={formatPct(value)}
      yoyPct={yoy}
      changeTone={yoy === null || yoy >= 0 ? "positive" : "negative"}
      sparkline={[]}
    />
  );
}

// ----------- CA-037: Debt-to-EBIT 4-case state machine ----------------------

function DebtToEbitSlot({
  debtToEbit,
  ebit,
}: {
  debtToEbit: KpiValueDto | null;
  ebit: KpiValueDto | null;
}) {
  const label = "Долг / EBIT";
  // Case 1: явный 0 — backend сигнализирует «нет долга» через Decimal(0).
  // == null ловит undefined тоже (если Docker API не пересобран после rename).
  if (debtToEbit != null && parseFloat(debtToEbit.value) === 0) {
    return <NoDebtCard label={label} />;
  }
  // Case 2: ratio есть и > 0 — обычный happy path.
  if (debtToEbit != null) {
    const value = parseFloat(debtToEbit.value);
    return (
      <KpiCard
        label={label}
        value={formatRatio(value)}
        yoyPct={null}
        changeTone="negative"
        sparkline={[]}
      />
    );
  }
  // Case 3: ratio null + ebit известен и ≤ 0 — убыток скрывает оценку.
  if (ebit != null && parseFloat(ebit.value) <= 0) {
    return (
      <EmptyKpiCard
        label={label}
        hint="Долговая нагрузка не оценима (убыток)"
        tone="danger"
      />
    );
  }
  // Case 4 (default): нет данных FORM_1 (debt = None) или ebit неизвестен.
  return <EmptyKpiCard label={label} hint="Загрузите Форму №1" />;
}

// ----------- Empty / no-debt cards ------------------------------------------

function EmptyKpiCard({
  label,
  hint,
  tooltip,
  tone = "neutral",
}: {
  label: string;
  hint: string;
  tooltip?: string;
  tone?: "neutral" | "danger";
}) {
  // CA-037: tone "danger" подсвечивает красным КПИ-карточку, когда null означает
  // конкретный финансовый сигнал (не «нет данных»), например ebit ≤ 0 для D/E.
  const border =
    tone === "danger" ? "border-[#F2BCBA] bg-[#FCE7E5]" : "border-[var(--ca-border)] bg-[var(--ca-surface)]";
  const labelColor =
    tone === "danger" ? "text-[var(--ca-danger)]" : "text-[var(--ca-ink-400)]";
  const hintColor =
    tone === "danger" ? "text-[var(--ca-danger)]" : "text-[var(--ca-ink-500)]";
  return (
    <div
      className={`rounded-[10px] border ${border} p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]`}
      title={tooltip}
    >
      <div className={`text-[10.5px] font-semibold tracking-[1.2px] uppercase ${labelColor}`}>
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ca-ink-400)]">
        —
      </div>
      <div className={`mt-2 text-[11.5px] ${hintColor}`}>{hint}</div>
      <div className="mt-3 h-[36px]" aria-hidden="true" />
    </div>
  );
}

function NoDebtCard({ label }: { label: string }) {
  // CA-037: total_debt = 0 — самостоятельный позитивный сигнал (нет долговой
  // нагрузки), а не «нет данных». Зелёный pill согласован с цветовой схемой
  // success в дизайне досье.
  return (
    <div className="rounded-[10px] border border-[#BFE2D2] bg-[var(--ca-success-50)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-success)] uppercase">
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ca-success)]">
        0,00×
      </div>
      <div className="mt-2 inline-flex items-center rounded-full bg-[var(--ca-success)] px-2 py-px text-[11px] font-semibold text-white">
        Нет долга
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
