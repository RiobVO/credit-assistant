// ADR-0024 (Session 2) — KpiRow с hide-empty контрактом.
// Проверяем: null KPI → карточка не рендерится (banker-clean align с PDF);
// value KPI → карточка с правильным форматом и level_tone stripe;
// NoDebtCard (Decimal 0) и quick_ratio добавлены к покрытию.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import ru from "../../i18n/ru.json";
import { KpiRow } from "./kpi-row";
import type { DossierViewDto, KpiValueDto } from "@/lib/api";

function _kpi(value: string, level_tone?: KpiValueDto["level_tone"]): KpiValueDto {
  return {
    value,
    unit: "RATIO",
    yoy_pct: null,
    sparkline: [],
    level_tone: level_tone ?? null,
  };
}

function _kpi_uzs(value: string): KpiValueDto {
  return {
    value,
    unit: "UZS",
    yoy_pct: null,
    sparkline: [],
    level_tone: null,
  };
}

const ALL_NULL_KPIS: DossierViewDto["kpis"] = {
  revenue_ltm: null,
  ebit: null,
  roe: null,
  debt_to_ebit: null,
  ebitda: null,
  debt_to_ebitda: null,
  current_ratio: null,
  working_capital: null,
  interest_coverage: null,
  dscr: null,
  // ADR-0024 Session 2:
  quick_ratio: null,
};

function renderRow(kpis: DossierViewDto["kpis"]) {
  // Readiness card дёргает API через React Query — оборачиваем в provider
  // с retry=false, чтобы тест не висел при network mock'е.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <NextIntlClientProvider locale="ru" messages={ru}>
        <KpiRow kpis={kpis} dossierId="00000000-0000-0000-0000-000000000000" />
      </NextIntlClientProvider>
    </QueryClientProvider>,
  );
}

describe("KpiRow — ADR-0024 Session 2 hide-empty contract", () => {
  it("все null KPI скрыты — labels не рендерятся в banker-clean view", () => {
    renderRow(ALL_NULL_KPIS);
    // Session 1 / Session 2 extended labels — все hidden при null.
    expect(screen.queryByText("EBITDA")).toBeNull();
    expect(screen.queryByText("Долг / EBITDA")).toBeNull();
    expect(screen.queryByText("Текущая ликвидность")).toBeNull();
    expect(screen.queryByText("Оборотный капитал")).toBeNull();
    expect(screen.queryByText("Покрытие процентов")).toBeNull();
    expect(screen.queryByText("DSCR")).toBeNull();
    expect(screen.queryByText("Quick Ratio")).toBeNull();
    // Legacy CA-037 labels тоже hidden при null.
    expect(screen.queryByText("EBIT (прокси EBITDA)")).toBeNull();
    expect(screen.queryByText("ROE")).toBeNull();
    expect(screen.queryByText("Долг / EBIT")).toBeNull();
  });

  it("hint-сообщения для пустых KPI убраны — banker не видит analyst-подсказок", () => {
    renderRow(ALL_NULL_KPIS);
    expect(
      screen.queryByText("Нужны PBT, проценты и D&A (амортизация)"),
    ).toBeNull();
    expect(
      screen.queryByText("Нужны краткосрочные активы, запасы и обязательства"),
    ).toBeNull();
  });

  it("current_ratio с tone good рендерится как ratio с stripe", () => {
    const kpis = { ...ALL_NULL_KPIS, current_ratio: _kpi("1.8", "good") };
    const { container } = renderRow(kpis);
    expect(screen.getByText("1,8x")).toBeInTheDocument();
    expect(screen.getByText("Текущая ликвидность")).toBeInTheDocument();
    // CA-048 left stripe: ищем элемент с border-l-4 классом.
    const stripeEl = container.querySelector(".border-l-4");
    expect(stripeEl).not.toBeNull();
  });

  it("debt_to_ebitda = 0 → NoDebtCard с зелёным pill (не hide)", () => {
    const kpis = { ...ALL_NULL_KPIS, debt_to_ebitda: _kpi("0") };
    renderRow(kpis);
    expect(screen.getByText("Нет долга")).toBeInTheDocument();
    expect(screen.getByText("0,00×")).toBeInTheDocument();
  });

  it("working_capital рендерит UZS-сумму через formatBigUzs", () => {
    const kpis = { ...ALL_NULL_KPIS, working_capital: _kpi_uzs("2000000000") };
    renderRow(kpis);
    // formatBigUzs выдаёт «2,0 млрд сум» (NBSP-separated)
    expect(screen.getByText(/2,0/)).toBeInTheDocument();
    expect(screen.getByText(/млрд/)).toBeInTheDocument();
  });

  it("dscr с tone bad даёт ratio и stripe", () => {
    const kpis = { ...ALL_NULL_KPIS, dscr: _kpi("0.9", "bad") };
    const { container } = renderRow(kpis);
    expect(screen.getByText("0,9x")).toBeInTheDocument();
    expect(container.querySelector(".border-l-4")).not.toBeNull();
  });

  it("quick_ratio с tone warn рендерится с ratio и stripe (ADR-0024 Session 2)", () => {
    const kpis = { ...ALL_NULL_KPIS, quick_ratio: _kpi("0.8", "warn") };
    const { container } = renderRow(kpis);
    expect(screen.getByText("Quick Ratio")).toBeInTheDocument();
    // formatRatio округляет до 1 знака после запятой.
    expect(screen.getByText("0,8x")).toBeInTheDocument();
    expect(container.querySelector(".border-l-4")).not.toBeNull();
  });

  it("quick_ratio с tone good рендерится без BAD stripe colour", () => {
    const kpis = { ...ALL_NULL_KPIS, quick_ratio: _kpi("1.5", "good") };
    renderRow(kpis);
    expect(screen.getByText("Quick Ratio")).toBeInTheDocument();
    expect(screen.getByText("1,5x")).toBeInTheDocument();
  });

  it("debt_to_ebit Case 3 (ebit ≤ 0) рендерит EmptyKpiCard danger — это сигнал, не пустота", () => {
    // ebit > 0 но debt_to_ebit null с ebit известным ≤ 0 — Case 3 (loss masks rating).
    // Это самостоятельный финансовый сигнал, оставляем (НЕ hide).
    const kpis = {
      ...ALL_NULL_KPIS,
      ebit: _kpi_uzs("-100000000"),
      debt_to_ebit: null,
    };
    renderRow(kpis);
    expect(screen.getByText("Долг / EBIT")).toBeInTheDocument();
  });
});
