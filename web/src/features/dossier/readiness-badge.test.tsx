// CA-040 smoke: проверяем что ReadinessBadge корректно рендерит ключевые
// поля ответа (level label, confidence %, missing_capabilities) и тихо
// ничего не рисует пока запрос летит — non-blocking контракт CA-035b.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getDossierReadiness: vi.fn(),
}));

import { getDossierReadiness } from "@/lib/api";

import ru from "../../i18n/ru.json";
import { ReadinessBadge } from "./readiness-badge";

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

describe("ReadinessBadge", () => {
  it("ничего не рендерит пока loading (non-blocking контракт)", () => {
    vi.mocked(getDossierReadiness).mockReturnValue(new Promise(() => {}));
    const { container } = renderWithClient(<ReadinessBadge dossierId="d-1" />);
    expect(container.firstChild).toBeNull();
  });

  it("standard 65% + 2 missing capabilities", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "standard",
      years_covered: [2024, 2025],
      full_years: [2025],
      missing_capabilities: ["yoy_trend", "balance_ratios"],
      parser_sources: ["manual", "form2"],
      confidence_score: "0.65",
    });

    renderWithClient(<ReadinessBadge dossierId="d-1" />);

    const pill = await screen.findByText(/Стандартный набор/);
    expect(pill).toBeInTheDocument();
    expect(pill).toHaveTextContent(/доверие 65%/);
    expect(screen.getByText(/Тренд YoY/)).toBeInTheDocument();
    expect(
      screen.getByText(/Балансовые коэффициенты \(FORM_1\)/),
    ).toBeInTheDocument();
  });

  it("comprehensive 100% без блока «Недоступно» когда missing пустой", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "comprehensive",
      years_covered: [2023, 2024, 2025],
      full_years: [2023, 2024, 2025],
      missing_capabilities: [],
      parser_sources: ["manual", "form1", "form2", "vat_declaration"],
      confidence_score: "1",
    });

    renderWithClient(<ReadinessBadge dossierId="d-1" />);

    const pill = await screen.findByText(/Полный набор/);
    expect(pill).toHaveTextContent(/доверие 100%/);
    expect(screen.queryByText(/Недоступно:/)).not.toBeInTheDocument();
  });

  it("insufficient 0% — заголовок «Недостаточно данных»", async () => {
    vi.mocked(getDossierReadiness).mockResolvedValue({
      level: "insufficient",
      years_covered: [],
      full_years: [],
      missing_capabilities: ["yoy_trend", "cagr", "balance_ratios", "tax_burden"],
      parser_sources: ["manual"],
      confidence_score: "0",
    });

    renderWithClient(<ReadinessBadge dossierId="d-1" />);

    const pill = await screen.findByText(/Недостаточно данных/);
    expect(pill).toHaveTextContent(/доверие 0%/);
  });
});
