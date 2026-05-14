// T0.4 follow-up B1: SignalRow source локализуется через useLocale().
// Backend всегда отдаёт source_uz (для old snapshot'ов = RU fallback);
// frontend выбирает RU/UZ по cookie ca_locale.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it } from "vitest";

import ru from "../../i18n/ru.json";
import uz from "../../i18n/uz.json";
import type { RedFlagDto } from "@/lib/api";
import { RiskSignals } from "./risk-signals";

const FLAG: RedFlagDto = {
  rule_id: "VAT_ESF_MISMATCH",
  rule_version: "v1",
  severity: "critical",
  source: "НК РУз ст. 256; Soliq внутренние методики",
  source_uz: "НК РУз ст. 256; Soliq ichki uslublari",
  message: "Декларация НДС vs ЭСФ расходится на 80%",
  message_uz: "QQS deklaratsiyasi va EHF 80% ga farqlanadi",
  evidence: {},
  detected_at: "2026-05-08",
};

function renderSignals(locale: "ru" | "uz", flag: RedFlagDto) {
  const messages = locale === "uz" ? uz : ru;
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      <RiskSignals flags={[flag]} rulesEvaluated={19} />
    </NextIntlClientProvider>,
  );
}

// Explicit cleanup: fireEvent.click меняет useState (expanded=true), accordion
// рендерит дополнительные nodes — без этого jsdom-singleton может пересекаться
// с тестами других файлов и ловить inter-file DOM-leaks.
afterEach(cleanup);

describe("RiskSignals source/message локализация", () => {
  it("locale=ru → RU source и RU message", () => {
    renderSignals("ru", FLAG);
    // Header collapsed: message виден в строке-saggetion.
    expect(
      screen.getAllByText("Декларация НДС vs ЭСФ расходится на 80%").length,
    ).toBeGreaterThan(0);
    // Expand accordion: source виден в footer.
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(
      screen.getByText("НК РУз ст. 256; Soliq внутренние методики"),
    ).toBeInTheDocument();
  });

  it("locale=uz → UZ source и UZ message", () => {
    renderSignals("uz", FLAG);
    expect(
      screen.getAllByText("QQS deklaratsiyasi va EHF 80% ga farqlanadi").length,
    ).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(
      screen.getByText("НК РУз ст. 256; Soliq ichki uslublari"),
    ).toBeInTheDocument();
  });

  it("locale=uz + пустой source_uz/message_uz → fallback на RU обоих полей", () => {
    const legacy: RedFlagDto = { ...FLAG, source_uz: "", message_uz: "" };
    renderSignals("uz", legacy);
    expect(
      screen.getAllByText("Декларация НДС vs ЭСФ расходится на 80%").length,
    ).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(
      screen.getByText("НК РУз ст. 256; Soliq внутренние методики"),
    ).toBeInTheDocument();
  });
});
