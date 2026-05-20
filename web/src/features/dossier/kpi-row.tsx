"use client";

import { useLocale, useTranslations } from "next-intl";

import type { DossierViewDto, KpiValueDto } from "@/lib/api";

import { formatBigUzs, formatPct, formatRatio, type UzsLocale } from "./format";

import { KpiCard } from "./kpi-card";
import { ReadinessKpiCard } from "./readiness-badge";

export function KpiRow({
  kpis,
  dossierId,
}: {
  kpis: DossierViewDto["kpis"];
  dossierId: string;
}) {
  const t = useTranslations("dossier.kpi");
  // ADR-0024 (Session 1): 10 KPI карточек = legacy 4 (EBIT/ROE/Debt-to-EBIT +
  // Readiness как замена revenue_ltm в этом ряду) + расширенные 6 (EBITDA /
  // Debt-to-EBITDA / Current Ratio / Working Capital / Interest Coverage / DSCR).
  // CA-037 invariant — legacy остаются рядом с расширением, не вместо.
  // Grid xl:grid-cols-4 → 10 cards в 3 ряда (4+4+2), читаемо без сжатия меток.
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <EbitSlot kpi={kpis.ebit} />
      <RoeSlot kpi={kpis.roe} />
      <DebtToEbitSlot debtToEbit={kpis.debt_to_ebit} ebit={kpis.ebit} />
      <ReadinessKpiCard dossierId={dossierId} label={t("label_readiness")} />
      {/* ADR-0024 (Session 1) — расширенный KPI набор: */}
      <EbitdaSlot kpi={kpis.ebitda} />
      <DebtToEbitdaSlot debtToEbitda={kpis.debt_to_ebitda} />
      <CurrentRatioSlot kpi={kpis.current_ratio} />
      <WorkingCapitalSlot kpi={kpis.working_capital} />
      <InterestCoverageSlot kpi={kpis.interest_coverage} />
      <DscrSlot kpi={kpis.dscr} />
    </div>
  );
}

// ----------- CA-037: EBIT slot with tooltip ---------------------------------

function EbitSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const locale = useLocale() as UzsLocale;
  // CA-037 контракт: пока depreciation/amortization недоступен, показываем EBIT
  // как прокси EBITDA. Tooltip объясняет honest scoping.
  const label = t("label_ebit");
  const tooltip = t("ebit_tooltip");
  if (kpi == null) {
    return (
      <EmptyKpiCard
        label={label}
        hint={t("ebit_empty_hint")}
        tooltip={tooltip}
      />
    );
  }
  const value = parseFloat(kpi.value);
  const yoy = kpi.yoy_pct !== null ? parseFloat(kpi.yoy_pct) : null;
  return (
    <KpiCard
      label={label}
      value={formatBigUzs(value, locale)}
      yoyPct={yoy}
      changeTone={yoy === null || yoy >= 0 ? "positive" : "negative"}
      tooltip={tooltip}
    />
  );
}

// ----------- CA-037: ROE slot with reason on null ---------------------------

function RoeSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const label = t("label_roe");
  if (kpi == null) {
    // Backend возвращает null когда equity_avg ≤ 0 или компоненты отсутствуют.
    // Без отдельного флага frontend не может различить эти две причины — даём
    // составную подсказку, которая корректна в обоих случаях.
    return <EmptyKpiCard label={label} hint={t("roe_empty_hint")} />;
  }
  const value = parseFloat(kpi.value);
  const yoy = kpi.yoy_pct !== null ? parseFloat(kpi.yoy_pct) : null;
  return (
    <KpiCard
      label={label}
      value={formatPct(value)}
      yoyPct={yoy}
      changeTone={yoy === null || yoy >= 0 ? "positive" : "negative"}
      levelTone={kpi.level_tone ?? undefined}
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
  const t = useTranslations("dossier.kpi");
  const label = t("label_debt_ebit");
  // Case 1: явный 0 — backend сигнализирует «нет долга» через Decimal(0).
  // == null ловит undefined тоже (если Docker API не пересобран после rename).
  if (debtToEbit != null && parseFloat(debtToEbit.value) === 0) {
    return <NoDebtCard label={label} pillLabel={t("no_debt_pill")} />;
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
        levelTone={debtToEbit.level_tone ?? undefined}
      />
    );
  }
  // Case 3: ratio null + ebit известен и ≤ 0 — убыток скрывает оценку.
  if (ebit != null && parseFloat(ebit.value) <= 0) {
    return (
      <EmptyKpiCard label={label} hint={t("debt_loss_hint")} tone="danger" />
    );
  }
  // Case 4 (default): нет данных FORM_1 (debt = None) или ebit неизвестен.
  return <EmptyKpiCard label={label} hint={t("debt_no_data_hint")} />;
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
    tone === "danger"
      ? "border-[var(--state-bad-border)] bg-[var(--state-bad-bg)]"
      : "border-[var(--border)] bg-[var(--surface)]";
  const labelColor =
    tone === "danger" ? "text-[var(--state-bad-fg)]" : "text-[var(--ink-4)]";
  const hintColor =
    tone === "danger" ? "text-[var(--state-bad-fg)]" : "text-[var(--ink-3)]";
  return (
    <div
      className={`rounded-[10px] border ${border} p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]`}
      title={tooltip}
    >
      <div className={`text-[10.5px] font-semibold tracking-[1.2px] uppercase ${labelColor}`}>
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ink-4)]">
        —
      </div>
      <div className={`mt-2 text-[11.5px] ${hintColor}`}>{hint}</div>
    </div>
  );
}

function NoDebtCard({ label, pillLabel }: { label: string; pillLabel: string }) {
  // CA-037: total_debt = 0 — самостоятельный позитивный сигнал (нет долговой
  // нагрузки), а не «нет данных». Зелёный pill согласован с цветовой схемой
  // success в дизайне досье.
  return (
    <div className="rounded-[10px] border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--state-ok-fg)] uppercase">
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--state-ok-fg)]">
        0,00×
      </div>
      <div className="mt-2 inline-flex items-center rounded-full bg-[var(--state-ok-fg)] px-2 py-px text-[11px] font-semibold text-white">
        {pillLabel}
      </div>
    </div>
  );
}

// =============================================================================
// ADR-0024 (Session 1): расширенный KPI набор
// =============================================================================
//
// 6 slot-компонентов по pattern legacy EbitSlot/RoeSlot. Все:
// * null → EmptyKpiCard с локализованным hint
// * value → KpiCard (UZS/RATIO formatting) + level_tone из backend
//
// Тонкие хвосты бэкенда обработаны:
// * debt_to_ebitda Decimal("0") = «нет долга» → NoDebtCard (как debt_to_ebit)
// * interest_coverage с отрицательным ratio (EBIT < 0) backend всё равно
//   возвращает KpiValue с tone BAD — frontend рендерит число, не «—»

// ----------- EBITDA ----------------------------------------------------------

function EbitdaSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const locale = useLocale() as UzsLocale;
  const label = t("label_ebitda");
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint={t("ebitda_empty_hint")} />;
  }
  const value = parseFloat(kpi.value);
  return (
    <KpiCard
      label={label}
      value={formatBigUzs(value, locale)}
      yoyPct={null}
      changeTone="positive"
    />
  );
}

// ----------- Debt / EBITDA — same 4-case как DebtToEbitSlot ------------------

function DebtToEbitdaSlot({ debtToEbitda }: { debtToEbitda: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const label = t("label_debt_ebitda");
  if (debtToEbitda != null && parseFloat(debtToEbitda.value) === 0) {
    return <NoDebtCard label={label} pillLabel={t("no_debt_pill")} />;
  }
  if (debtToEbitda != null) {
    return (
      <KpiCard
        label={label}
        value={formatRatio(parseFloat(debtToEbitda.value))}
        yoyPct={null}
        changeTone="negative"
        levelTone={debtToEbitda.level_tone ?? undefined}
      />
    );
  }
  return <EmptyKpiCard label={label} hint={t("debt_ebitda_empty_hint")} />;
}

// ----------- Current Ratio ---------------------------------------------------

function CurrentRatioSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const label = t("label_current_ratio");
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint={t("current_ratio_empty_hint")} />;
  }
  return (
    <KpiCard
      label={label}
      value={formatRatio(parseFloat(kpi.value))}
      yoyPct={null}
      changeTone="positive"
      levelTone={kpi.level_tone ?? undefined}
    />
  );
}

// ----------- Working Capital -------------------------------------------------

function WorkingCapitalSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const locale = useLocale() as UzsLocale;
  const label = t("label_working_capital");
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint={t("working_capital_empty_hint")} />;
  }
  const value = parseFloat(kpi.value);
  // Знак — единственный сигнал WC (нет universal threshold). Отрицательный WC
  // визуально оборачиваем в negative tone без BAD stripe.
  return (
    <KpiCard
      label={label}
      value={formatBigUzs(value, locale)}
      yoyPct={null}
      changeTone={value >= 0 ? "positive" : "negative"}
    />
  );
}

// ----------- Interest Coverage -----------------------------------------------

function InterestCoverageSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const label = t("label_interest_coverage");
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint={t("interest_coverage_empty_hint")} />;
  }
  return (
    <KpiCard
      label={label}
      value={formatRatio(parseFloat(kpi.value))}
      yoyPct={null}
      changeTone="positive"
      levelTone={kpi.level_tone ?? undefined}
    />
  );
}

// ----------- DSCR ------------------------------------------------------------

function DscrSlot({ kpi }: { kpi: KpiValueDto | null }) {
  const t = useTranslations("dossier.kpi");
  const label = t("label_dscr");
  if (kpi == null) {
    return <EmptyKpiCard label={label} hint={t("dscr_empty_hint")} />;
  }
  return (
    <KpiCard
      label={label}
      value={formatRatio(parseFloat(kpi.value))}
      yoyPct={null}
      changeTone="positive"
      levelTone={kpi.level_tone ?? undefined}
    />
  );
}
