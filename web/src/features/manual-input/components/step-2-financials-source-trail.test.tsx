// CA-DS23: RTL-тесты на source-trail rendering в Step2Financials.
//
// Покрываем два независимых модуля:
//   1. SourceHint — текст-подсказка под полем для каждого state
//      (auto / manual / manual-required / waiting).
//   2. UzsInputShell — borderbar (3px absolute span слева) + UZS-suffix
//      tone в зависимости от source state и invalid prop.

import { act, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useLayoutEffect, useRef } from "react";
import { FormProvider, useForm, type UseFormReturn } from "react-hook-form";
import { describe, expect, it } from "vitest";

import ru from "../../../i18n/ru.json";
import { SourceTrailProvider, useSourceTrail } from "../hooks/use-source-trail";
import type { FormValues } from "../schema";
import {
  SourceHint,
  UzsInputShell,
  useFieldSourceState,
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

  // CA-DS21 — auto-edited 3-state
  it("auto-edited state → info hint с «s2_source_auto_edited»", () => {
    render(withIntl(<SourceHint state="auto-edited" />));
    expect(
      screen.getByText(ru.accountant.manual_input.s2_source_auto_edited),
    ).toBeInTheDocument();
    const hint = screen
      .getByText(ru.accountant.manual_input.s2_source_auto_edited)
      .closest("div");
    expect(hint?.className).toContain("text-[var(--state-info-fg)]");
  });

  it("auto-edited + fieldName → SourceTag «FORM_2» (info-tone)", () => {
    render(
      withIntl(
        <SourceHint
          state="auto-edited"
          fieldName="step2.revenue.y2025.annual"
        />,
      ),
    );
    const tag = screen.getByText("FORM_2");
    expect(tag).toBeInTheDocument();
    expect(tag.className).toContain("bg-[var(--state-info-bg)]");
    expect(tag.className).toContain("text-[var(--state-info-fg)]");
  });

  it("auto-edited hint показывает auto_edited_hint suffix", () => {
    render(withIntl(<SourceHint state="auto-edited" />));
    expect(
      screen.getByText(
        new RegExp(ru.accountant.manual_input.s2_source_auto_edited_hint),
      ),
    ).toBeInTheDocument();
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

  // CA-DS21 — auto-edited borderbar + suffix
  it("state=auto-edited → borderbar info-синий (state-info-fg)", () => {
    const { borderbar } = shellOf("auto-edited");
    expect(borderbar?.className).toContain("bg-[var(--state-info-fg)]");
  });

  it("state=auto-edited → UZS-suffix нейтральный (без ok-bg)", () => {
    // Дизайн-инвариант: borderbar — единственный info-marker, suffix
    // остаётся нейтральным чтобы не перегружать визуал.
    const { suffix } = shellOf("auto-edited");
    const tile = suffix.closest("div");
    expect(tile?.className).not.toContain("bg-[var(--state-ok-bg)]");
    expect(tile?.className).toContain("bg-[var(--surface-2)]");
  });

  it("invalid + auto-edited → suffix bad (parser-cap снят правкой)", () => {
    // Когда пользователь поправил parser-ское значение, parser-validated
    // invariant больше не действует — invalid prop должен показаться как
    // обычно (в отличие от auto, где invalid игнорируется).
    const { suffix } = shellOf("auto-edited", true);
    const tile = suffix.closest("div");
    expect(tile?.className).toContain("bg-[var(--state-bad-bg)]");
  });
});

// ─────────── CA-DS21: useFieldSourceState integration ───────────────────
//
// Покрываем цепочку: parsedValues + form value → SourceState. Через
// HookProbe component получаем состояние из data-testid и проверяем
// reactivity (mergeParsedValues, form.setValue → re-evaluation).

describe("useFieldSourceState (CA-DS21)", () => {
  type ProbeProps = {
    fieldName: string;
    forceManualRequired?: boolean;
  };
  type HarnessHandle = {
    form: UseFormReturn<FormValues>;
    trail: ReturnType<typeof useSourceTrail> | null;
  };

  function HookProbe({ fieldName, forceManualRequired }: ProbeProps) {
    const state = useFieldSourceState(fieldName, { forceManualRequired });
    return <div data-testid="state-probe">{state}</div>;
  }

  function TrailCapture({ handle }: { handle: HarnessHandle }) {
    handle.trail = useSourceTrail();
    return null;
  }

  function ParsedSeeder({ seed }: { seed: Record<string, string> }) {
    const { mergeParsedValues } = useSourceTrail();
    const seededRef = useRef(false);
    useLayoutEffect(() => {
      if (seededRef.current) return;
      seededRef.current = true;
      if (Object.keys(seed).length > 0) mergeParsedValues(seed);
    }, [mergeParsedValues, seed]);
    return null;
  }

  function renderHarness(
    initialValue: string,
    parsedSeed: Record<string, string>,
    probeProps: ProbeProps,
  ): HarnessHandle {
    const handle: HarnessHandle = {
      form: undefined as never as UseFormReturn<FormValues>,
      trail: null,
    };
    function Inner() {
      const form = useForm<FormValues>({
        // Только нужное поле — react-hook-form допускает sparse defaults.
        defaultValues: {
          step2: { totalAssets: initialValue },
        } as Partial<FormValues> as FormValues,
      });
      handle.form = form;
      return (
        <NextIntlClientProvider locale="ru" messages={ru}>
          <SourceTrailProvider>
            <FormProvider {...form}>
              <TrailCapture handle={handle} />
              <ParsedSeeder seed={parsedSeed} />
              <HookProbe {...probeProps} />
            </FormProvider>
          </SourceTrailProvider>
        </NextIntlClientProvider>
      );
    }
    render(<Inner />);
    return handle;
  }

  it("parsed[fieldName] === current → auto", () => {
    renderHarness(
      "5000000",
      { "step2.totalAssets": "5000000" },
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("auto");
  });

  it("parsed[fieldName] !== current → auto-edited", () => {
    renderHarness(
      "5000001",
      { "step2.totalAssets": "5000000" },
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("auto-edited");
  });

  it("parsed[fieldName] === '5000000', user clears → auto-edited (Q2)", () => {
    renderHarness(
      "",
      { "step2.totalAssets": "5000000" },
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("auto-edited");
  });

  it("parsedValues пустой + value присутствует → manual", () => {
    renderHarness(
      "1000000",
      {},
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("manual");
  });

  it("parsedValues пустой + value пустой → waiting", () => {
    renderHarness("", {}, { fieldName: "step2.totalAssets" });
    expect(screen.getByTestId("state-probe").textContent).toBe("waiting");
  });

  it("forceManualRequired перевешивает всё → manual-required", () => {
    renderHarness(
      "5000000",
      { "step2.totalAssets": "5000000" },
      { fieldName: "step2.totalAssets", forceManualRequired: true },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe(
      "manual-required",
    );
  });

  it("transition auto → auto-edited при правке value", () => {
    const handle = renderHarness(
      "5000000",
      { "step2.totalAssets": "5000000" },
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("auto");
    act(() => {
      handle.form.setValue("step2.totalAssets" as never, "5000001" as never);
    });
    expect(screen.getByTestId("state-probe").textContent).toBe("auto-edited");
  });

  it("transition waiting → auto при mergeParsedValues + matching value", () => {
    const handle = renderHarness(
      "7000000",
      {},
      { fieldName: "step2.totalAssets" },
    );
    expect(screen.getByTestId("state-probe").textContent).toBe("manual");
    act(() => {
      handle.trail?.mergeParsedValues({ "step2.totalAssets": "7000000" });
    });
    expect(screen.getByTestId("state-probe").textContent).toBe("auto");
  });
});
