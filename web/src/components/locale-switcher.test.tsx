// CA-DS29: RTL для LocaleSwitcher — current locale из useLocale, выбор
// другой опции триггерит server action.

import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import ru from "../i18n/ru.json";

// Mock server action — RSC mutations не работают в jsdom; нам важно
// что компонент вызвал action с правильным аргументом.
const setLocaleAction = vi.fn();
vi.mock("@/app/_actions/set-locale", () => ({
  setLocaleAction: (locale: string) => setLocaleAction(locale),
}));

import { LocaleSwitcher } from "./locale-switcher";

function renderSwitcher(locale: "ru" | "uz" = "ru") {
  return render(
    <NextIntlClientProvider locale={locale} messages={ru}>
      <LocaleSwitcher />
    </NextIntlClientProvider>,
  );
}

describe("LocaleSwitcher (CA-DS29)", () => {
  it("показывает current locale в dropdown", () => {
    renderSwitcher("ru");
    expect(screen.getByRole("combobox")).toHaveTextContent("RU");
  });

  it("aria-label на group из локализованного string", () => {
    renderSwitcher("ru");
    const group = screen.getByRole("group");
    expect(group).toHaveAttribute(
      "aria-label",
      ru.shared.topbar.locale_switcher_aria,
    );
  });

  it("открытие dropdown показывает обе опции (RU + UZ)", () => {
    renderSwitcher("ru");
    fireEvent.click(screen.getByRole("combobox"));
    const options = screen.getAllByRole("option");
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("RU");
    expect(options[1]).toHaveTextContent("UZ");
  });

  it("выбор другой локали вызывает setLocaleAction с её id", () => {
    setLocaleAction.mockClear();
    renderSwitcher("ru");
    fireEvent.click(screen.getByRole("combobox"));
    const options = screen.getAllByRole("option");
    fireEvent.click(options[1]);
    expect(setLocaleAction).toHaveBeenCalledWith("uz");
  });

  it("выбор same locale НЕ вызывает action (no-op)", () => {
    setLocaleAction.mockClear();
    renderSwitcher("ru");
    fireEvent.click(screen.getByRole("combobox"));
    const options = screen.getAllByRole("option");
    fireEvent.click(options[0]);
    expect(setLocaleAction).not.toHaveBeenCalled();
  });
});
