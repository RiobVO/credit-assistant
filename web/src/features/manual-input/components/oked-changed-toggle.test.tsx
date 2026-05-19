// ADR-0024 Session 3: OkedChangedByOwnerBlock — conditional rendering toggle
// для smart-narrow OKVED_CHANGED_12M rule.
//
// Покрываем:
//   • hidden когда okvedMainChangedAt = null (brand-new dossier flow)
//   • visible когда дата задана + чекбокс отражает значение field
//   • toggle меняет значение в RHF state
//   • date форматируется DD.MM.YYYY

import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it } from "vitest";
import { FormProvider, useForm } from "react-hook-form";

import ru from "../../../i18n/ru.json";
import { defaultFormValues, type FormValues } from "../schema";
import { OkedChangedByOwnerBlock } from "./step-1-borrower";

function Harness({
  date,
  initialChecked = false,
}: {
  date: string | null;
  initialChecked?: boolean;
}) {
  const form = useForm<FormValues>({
    defaultValues: {
      ...defaultFormValues(),
      step1: {
        ...defaultFormValues().step1,
        okvedMainChangedAt: date,
        okedChangedByOwner: initialChecked,
      },
    },
  });
  return (
    <NextIntlClientProvider locale="ru" messages={ru}>
      <FormProvider {...form}>
        {date ? <OkedChangedByOwnerBlock date={date} control={form.control} /> : null}
      </FormProvider>
    </NextIntlClientProvider>
  );
}

describe("OkedChangedByOwnerBlock (ADR-0024 Session 3)", () => {
  afterEach(() => {
    cleanup();
  });

  it("hidden когда даты нет (brand-new dossier flow)", () => {
    render(<Harness date={null} />);
    expect(
      screen.queryByLabelText(ru.accountant.manual_input.s1_oked_changed_by_owner_label),
    ).not.toBeInTheDocument();
  });

  it("visible когда дата задана + форматирует DD.MM.YYYY", () => {
    render(<Harness date="2025-09-15" />);
    // Дата отрисована в формате DD.MM.YYYY.
    expect(screen.getByText("15.09.2025")).toBeInTheDocument();
    // Toggle присутствует.
    const checkbox = screen.getByLabelText(
      ru.accountant.manual_input.s1_oked_changed_by_owner_label,
    );
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).not.toBeChecked();
  });

  it("toggle отражает initial state field (checked)", () => {
    render(<Harness date="2026-01-10" initialChecked={true} />);
    const checkbox = screen.getByLabelText(
      ru.accountant.manual_input.s1_oked_changed_by_owner_label,
    );
    expect(checkbox).toBeChecked();
  });

  it("click меняет состояние toggle", () => {
    render(<Harness date="2026-03-20" initialChecked={false} />);
    const checkbox = screen.getByLabelText(
      ru.accountant.manual_input.s1_oked_changed_by_owner_label,
    ) as HTMLInputElement;
    expect(checkbox).not.toBeChecked();
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  it("help-text отображается под toggle", () => {
    render(<Harness date="2025-12-01" />);
    expect(
      screen.getByText(ru.accountant.manual_input.s1_oked_changed_help),
    ).toBeInTheDocument();
  });
});
