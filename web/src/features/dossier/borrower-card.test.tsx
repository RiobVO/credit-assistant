// T0.3.2 — BorrowerCard ГНК pill: показ статуса справки + источника.
// Без справки — pill отсутствует физически (Phase 9 lesson, mock UI на decision
// screens).

import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import ru from "../../i18n/ru.json";
import { BorrowerCard } from "./borrower-card";
import type { DossierViewDto } from "@/lib/api";

const BORROWER: DossierViewDto["borrower"] = {
  inn: "305002665",
  name: "TEST",
  legal_form: "llc",
  registration_date: "2020-01-01",
  director_name: "Test Director",
  director_appointed_at: "2024-01-01",
  oked_main: "47.11",
  registered_address: "Tashkent",
  oked_main_changed_at: null,
  charter_capital: null,
  oked_changed_by_owner: false,
};

function renderCard(gnkCertificate: DossierViewDto["gnk_certificate"]) {
  return render(
    <NextIntlClientProvider locale="ru" messages={ru}>
      <BorrowerCard borrower={BORROWER} gnkCertificate={gnkCertificate} />
    </NextIntlClientProvider>,
  );
}

describe("BorrowerCard gnk badge", () => {
  it("без справки — pill отсутствует, row справки тоже", () => {
    renderCard(null);
    expect(screen.queryByTestId("gnk-badge")).not.toBeInTheDocument();
    expect(screen.queryByText(/Справка ГНК/)).not.toBeInTheDocument();
  });

  it("active uploaded — green pill + источник 'загружено аналитиком'", () => {
    renderCard({
      file_id: "f1",
      full_name: "X",
      status: "active",
      okveds: ["47.11"],
      source: "uploaded",
      cert_id: "GNK-1",
      uploaded_at: "2026-05-18T10:00:00Z",
    });
    const badge = screen.getByTestId("gnk-badge");
    expect(badge).toHaveAttribute("data-status", "active");
    expect(badge).toHaveTextContent("Активный плательщик НДС");
    expect(badge).toHaveTextContent("загружено аналитиком");
    expect(screen.getByText("GNK-1")).toBeInTheDocument();
  });

  it("revoked — bad-tone pill", () => {
    renderCard({
      file_id: null,
      full_name: "X",
      status: "revoked",
      okveds: [],
      source: "uploaded",
      cert_id: null,
      uploaded_at: null,
    });
    const badge = screen.getByTestId("gnk-badge");
    expect(badge).toHaveAttribute("data-status", "revoked");
    expect(badge).toHaveTextContent("Снят с учёта НДС");
  });
});
