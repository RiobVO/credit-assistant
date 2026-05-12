// CA-040 smoke + post-design-parity: ReadinessKpiCard рендерит confidence%,
// uppercase level + parser sources в подзаголовке, цветную stripe по level.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getDossierReadiness: vi.fn(),
}));

import { getDossierReadiness } from "@/lib/api";

import ru from "../../i18n/ru.json";
import { ReadinessKpiCard } from "./readiness-badge";

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  return render(
    <NextIntlClientProvider locale="ru" messages={ru}>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe("ReadinessKpiCard", () => {
  it("loading: показывает прочерк + подзаголовок «Загружаем оценку…»", () => {
    vi.mocked(getDossierReadiness).mockReturnValue(new Promise(() => {}));
    renderWithClient(<ReadinessKpiCard dossierId="d-1" label="Готовность данных" />);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText(/Загружаем оценку/)).toBeInTheDocument();
  });

  it("standard 65% — value «65 %», подзаголовок UPPERCASE level + sources", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "standard",
      years_covered: [2024, 2025],
      full_years: [2025],
      missing_capabilities: ["yoy_trend", "balance_ratios"],
      parser_sources: ["form1", "form2"],
      confidence_score: "0.65",
    });

    renderWithClient(<ReadinessKpiCard dossierId="d-1" label="Готовность данных" />);

    expect(await screen.findByText("65 %")).toBeInTheDocument();
    expect(screen.getByText(/СТАНДАРТНЫЙ НАБОР · Form 1 \+ Form 2/)).toBeInTheDocument();
  });

  it("comprehensive 100% — value «100 %», good-tone stripe", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "comprehensive",
      years_covered: [2023, 2024, 2025],
      full_years: [2023, 2024, 2025],
      missing_capabilities: [],
      parser_sources: ["form1", "form2", "vat_declaration"],
      confidence_score: "1",
    });

    const { container } = renderWithClient(
      <ReadinessKpiCard dossierId="d-1" label="Готовность данных" />,
    );

    expect(await screen.findByText("100 %")).toBeInTheDocument();
    expect(
      screen.getByText(/ПОЛНЫЙ НАБОР · Form 1 \+ Form 2 \+ VAT decl\./),
    ).toBeInTheDocument();
    // good-tone stripe — присутствует utility-класс с border-l-4 + ok-fg.
    expect(container.querySelector(".border-l-4")).toBeInTheDocument();
  });

  it("insufficient 0% — bad-tone stripe", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "insufficient",
      years_covered: [],
      full_years: [],
      missing_capabilities: ["yoy_trend", "cagr"],
      parser_sources: ["manual"],
      confidence_score: "0",
    });

    renderWithClient(<ReadinessKpiCard dossierId="d-1" label="Готовность данных" />);

    expect(await screen.findByText("0 %")).toBeInTheDocument();
    expect(screen.getByText(/НЕДОСТАТОЧНО ДАННЫХ · Manual/)).toBeInTheDocument();
  });
});
