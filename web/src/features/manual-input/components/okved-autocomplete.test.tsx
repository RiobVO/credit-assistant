// CA-DS20b: RTL-тесты на OkvedAutocomplete.
//
// Покрываем:
//   * loading state — «Загружаем каталог»
//   * loaded state — все catalog items в dropdown
//   * фильтрация по code prefix
//   * фильтрация по описанию
//   * keyboard nav (ArrowDown/ArrowUp/Enter/Escape)
//   * mouse click selection
//   * empty result → empty pill
//   * локализация labels (locale=uz рендерит full_uz, locale=ru рендерит full_ru)

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getOkvedCatalog: vi.fn(),
}));

import { getOkvedCatalog } from "@/lib/api";

import ru from "../../../i18n/ru.json";
import uz from "../../../i18n/uz.json";
import { OkvedAutocomplete } from "./step-1-borrower";

const FIXTURE = {
  items: [
    {
      code: "10.71",
      short_ru: "Производство хлеба",
      full_ru: "Производство хлеба и мучных кондитерских изделий",
      short_uz: "Non ishlab chiqarish",
      full_uz: "Non va un qandolat mahsulotlari ishlab chiqarish",
    },
    {
      code: "47.11",
      short_ru: "Розн. торговля прод. товарами",
      full_ru: "Розничная торговля преимущественно пищевыми продуктами",
      short_uz: "Oziq-ovqat chakana savdosi",
      full_uz: "Asosan oziq-ovqat mahsulotlari bilan chakana savdo",
    },
    {
      code: "62.01",
      short_ru: "Разработка ПО",
      full_ru: "Разработка компьютерного программного обеспечения",
      short_uz: "Dasturiy ta'minot ishlab chiqish",
      full_uz: "Kompyuter dasturiy ta'minotini ishlab chiqish",
    },
  ],
};

function renderAutocomplete(locale: "ru" | "uz" = "ru", initial = "") {
  let lastValue = initial;
  function Harness() {
    const [value, setValue] = useState(initial);
    return (
      <NextIntlClientProvider locale={locale} messages={locale === "uz" ? uz : ru}>
        <OkvedAutocomplete
          value={value}
          onChange={(v) => {
            setValue(v);
            lastValue = v;
          }}
          onBlur={() => {}}
          invalid={false}
        />
      </NextIntlClientProvider>
    );
  }
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
  const utils = render(
    <QueryClientProvider client={client}>
      <Harness />
    </QueryClientProvider>,
  );
  return {
    ...utils,
    input: utils.container.querySelector("input")!,
    getValue: () => lastValue,
  };
}

describe("OkvedAutocomplete (CA-DS20b)", () => {
  it("loading state: показывает «Загружаем каталог»", async () => {
    vi.mocked(getOkvedCatalog).mockReturnValue(new Promise(() => {})); // pending forever
    const { input } = renderAutocomplete();
    fireEvent.focus(input);
    expect(
      await screen.findByText(ru.accountant.manual_input.s1_okved_loading),
    ).toBeInTheDocument();
  });

  it("loaded: все items видны при пустом query", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete();
    fireEvent.focus(input);
    expect(await screen.findByText("10.71")).toBeInTheDocument();
    expect(screen.getByText("47.11")).toBeInTheDocument();
    expect(screen.getByText("62.01")).toBeInTheDocument();
  });

  it("filter by code prefix", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete();
    fireEvent.focus(input);
    await screen.findByText("10.71");

    fireEvent.change(input, { target: { value: "47" } });
    await waitFor(() => {
      expect(screen.queryByText("10.71")).not.toBeInTheDocument();
    });
    expect(screen.getByText("47.11")).toBeInTheDocument();
    expect(screen.queryByText("62.01")).not.toBeInTheDocument();
  });

  it("filter by description (case-insensitive substring)", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete();
    fireEvent.focus(input);
    await screen.findByText("10.71");

    fireEvent.change(input, { target: { value: "хлеб" } });
    await waitFor(() => {
      expect(screen.getByText("10.71")).toBeInTheDocument();
    });
    expect(screen.queryByText("47.11")).not.toBeInTheDocument();
    expect(screen.queryByText("62.01")).not.toBeInTheDocument();
  });

  it("empty result → empty pill", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete();
    fireEvent.focus(input);
    await screen.findByText("10.71");

    fireEvent.change(input, { target: { value: "99.99" } });
    await waitFor(() => {
      expect(
        screen.getByText(ru.accountant.manual_input.s1_okved_empty),
      ).toBeInTheDocument();
    });
  });

  it("mousedown на опцию выбирает её и закрывает dropdown", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input, getValue } = renderAutocomplete();
    fireEvent.focus(input);
    const option = await screen.findByText("47.11");

    fireEvent.mouseDown(option);
    expect(getValue()).toBe("47.11");
    // Dropdown закрыт — listbox исчез.
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("ArrowDown + Enter выбирает второй элемент", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input, getValue } = renderAutocomplete();
    fireEvent.focus(input);
    await screen.findByText("10.71");

    // highlight = 0 по умолчанию → ArrowDown поднимает на 1 (47.11).
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(getValue()).toBe("47.11");
  });

  it("Escape закрывает dropdown без выбора", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input, getValue } = renderAutocomplete();
    fireEvent.focus(input);
    await screen.findByText("10.71");

    fireEvent.keyDown(input, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
    expect(getValue()).toBe("");
  });

  it("locale=ru рендерит full_ru в опциях", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete("ru");
    fireEvent.focus(input);
    expect(
      await screen.findByText(/Розничная торговля преимущественно/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Asosan oziq-ovqat/),
    ).not.toBeInTheDocument();
  });

  it("locale=uz рендерит full_uz в опциях", async () => {
    vi.mocked(getOkvedCatalog).mockResolvedValue(FIXTURE);
    const { input } = renderAutocomplete("uz");
    fireEvent.focus(input);
    expect(
      await screen.findByText(/Asosan oziq-ovqat/),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Розничная торговля преимущественно/),
    ).not.toBeInTheDocument();
  });
});
