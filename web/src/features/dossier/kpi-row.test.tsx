// ADR-0024 (Session 1) — KpiRow с расширенным набором KPI.
// Проверяем: новые карточки рендерятся; null → EmptyKpiCard с hint;
// level_tone из backend становится stripe.

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

describe("KpiRow — ADR-0024 extended KPI set", () => {
  it("все 6 новых меток присутствуют в degraded mode (null значения)", () => {
    renderRow(ALL_NULL_KPIS);
    expect(screen.getByText("EBITDA")).toBeInTheDocument();
    expect(screen.getByText("Долг / EBITDA")).toBeInTheDocument();
    expect(screen.getByText("Текущая ликвидность")).toBeInTheDocument();
    expect(screen.getByText("Оборотный капитал")).toBeInTheDocument();
    expect(screen.getByText("Покрытие процентов")).toBeInTheDocument();
    expect(screen.getByText("DSCR")).toBeInTheDocument();
  });

  it("null EBITDA → empty hint", () => {
    renderRow(ALL_NULL_KPIS);
    expect(screen.getByText("Нужны PBT, проценты и D&A (амортизация)")).toBeInTheDocument();
  });

  it("current_ratio с tone good рендерится как ratio с stripe", () => {
    const kpis = { ...ALL_NULL_KPIS, current_ratio: _kpi("1.8", "good") };
    const { container } = renderRow(kpis);
    expect(screen.getByText("1,8x")).toBeInTheDocument();
    // CA-048 left stripe: ищем элемент с border-l-4 классом.
    const stripeEl = container.querySelector(".border-l-4");
    expect(stripeEl).not.toBeNull();
  });

  it("debt_to_ebitda = 0 → NoDebtCard с зелёным pill", () => {
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
});
