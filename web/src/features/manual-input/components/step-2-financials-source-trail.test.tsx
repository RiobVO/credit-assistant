// CA-DS23: RTL-тесты на source-trail rendering в Step2Financials.
//
// Покрываем два независимых модуля:
//   1. SourceHint — текст-подсказка под полем для каждого state
//      (auto / manual / manual-required / waiting).
//   2. UzsInputShell — borderbar (3px absolute span слева) + UZS-suffix
//      tone в зависимости от source state и invalid prop.

import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import ru from "../../../i18n/ru.json";
import {
  SourceHint,
  UzsInputShell,
  type SourceState,
} from "./step-2-financials";

function withIntl(node: React.ReactNode) {
  return (
    <NextIntlClientProvider locale="ru" messages={ru}>
      {node}
    </NextIntlClientProvider>
  );
}

describe("SourceHint (CA-DS23)", () => {
  it("auto state → green hint с «s2_source_auto»", () => {
    render(withIntl(<SourceHint state="auto" />));
    expect(
      screen.getByText(ru.accountant.manual_input.s2_source_auto),
    ).toBeInTheDocument();
    // hint-контейнер имеет text-class state-ok-fg.
    const hint = screen.getByText(ru.accountant.manual_input.s2_source_auto)
      .closest("div");
    expect(hint?.className).toContain("text-[var(--state-ok-fg)]");
  });

  it("manual state → grey hint с «s2_source_manual»", () => {
    render(withIntl(<SourceHint state="manual" />));
    expect(
      screen.getByText(ru.accountant.manual_input.s2_source_manual),
    ).toBeInTheDocument();
    const hint = screen.getByText(ru.accountant.manual_input.s2_source_manual)
      .closest("div");
    expect(hint?.className).toContain("text-[var(--ink-4)]");
  });

  it("manual-required state → amber hint с «s2_source_manual_required»", () => {
    render(withIntl(<SourceHint state="manual-required" />));
    expect(
      screen.getByText(ru.accountant.manual_input.s2_source_manual_required),
    ).toBeInTheDocument();
    const hint = screen
      .getByText(ru.accountant.manual_input.s2_source_manual_required)
      .closest("div");
    expect(hint?.className).toContain("text-[var(--state-warn-fg)]");
  });

  it("waiting state → muted hint с «s2_source_waiting» + «?» icon", () => {
    render(withIntl(<SourceHint state="waiting" />));
    expect(
      screen.getByText(ru.accountant.manual_input.s2_source_waiting),
    ).toBeInTheDocument();
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("auto + fieldName → SourceTag «FORM_2» (ok-tone)", () => {
    render(
      withIntl(
        <SourceHint state="auto" fieldName="step2.revenue.y2025.annual" />,
      ),
    );
    const tag = screen.getByText("FORM_2");
    expect(tag).toBeInTheDocument();
    expect(tag.className).toContain("bg-[var(--state-ok-bg)]");
  });

  it("waiting + fieldName → SourceTag «FORM_1» в muted-tone", () => {
    render(
      withIntl(<SourceHint state="waiting" fieldName="step2.totalAssets" />),
    );
    const tag = screen.getByText("FORM_1");
    expect(tag).toBeInTheDocument();
    expect(tag.className).toContain("bg-[var(--surface-2)]");
  });

  it("manual state БЕЗ SourceTag (даже с fieldName)", () => {
    render(
      withIntl(
        <SourceHint state="manual" fieldName="step2.revenue.y2025.annual" />,
      ),
    );
    expect(screen.queryByText("FORM_2")).not.toBeInTheDocument();
  });
});

describe("UzsInputShell borderbar (CA-DS23)", () => {
  function shellOf(state: SourceState, invalid = false) {
    const { container } = render(
      withIntl(
        <UzsInputShell state={state} invalid={invalid}>
          <input data-testid="shell-input" />
        </UzsInputShell>,
      ),
    );
    const borderbar = container.querySelector("span[aria-hidden]");
    const suffix = screen.getByText("UZS");
    return { borderbar, suffix };
  }

  it("state=auto → borderbar зелёный (state-ok-fg)", () => {
    const { borderbar } = shellOf("auto");
    expect(borderbar?.className).toContain("bg-[var(--state-ok-fg)]");
  });

  it("state=manual-required → borderbar amber (state-warn-fg + opacity-60)", () => {
    const { borderbar } = shellOf("manual-required");
    expect(borderbar?.className).toContain("bg-[var(--state-warn-fg)]");
    expect(borderbar?.className).toContain("opacity-60");
  });

  it("state=manual → borderbar без bg-class (нейтральный)", () => {
    const { borderbar } = shellOf("manual");
    expect(borderbar?.className).not.toContain("bg-[var(--state-ok-fg)]");
    expect(borderbar?.className).not.toContain("bg-[var(--state-warn-fg)]");
  });

  it("state=waiting → borderbar без bg-class (нейтральный)", () => {
    const { borderbar } = shellOf("waiting");
    expect(borderbar?.className).not.toContain("bg-[var(--state-ok-fg)]");
    expect(borderbar?.className).not.toContain("bg-[var(--state-warn-fg)]");
  });

  it("state=auto → UZS-suffix зелёный (state-ok-bg)", () => {
    const { suffix } = shellOf("auto");
    const tile = suffix.closest("div");
    expect(tile?.className).toContain("bg-[var(--state-ok-bg)]");
  });

  it("invalid + non-auto → UZS-suffix красный (state-bad-bg)", () => {
    const { suffix } = shellOf("manual", true);
    const tile = suffix.closest("div");
    expect(tile?.className).toContain("bg-[var(--state-bad-bg)]");
  });

  it("invalid + auto → suffix остаётся ok (auto перевешивает invalid)", () => {
    // Дизайн-инвариант: если поле автозаполнено, то технически валидно
    // (parser проставил), invalid prop не должен затмить ok-tone.
    const { suffix } = shellOf("auto", true);
    const tile = suffix.closest("div");
    expect(tile?.className).toContain("bg-[var(--state-ok-bg)]");
    expect(tile?.className).not.toContain("bg-[var(--state-bad-bg)]");
  });
});
