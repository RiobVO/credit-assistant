// Phase 6: DatePicker smoke — open / pick / clear / disabled past `max`.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { describe, it, expect, vi } from "vitest";

import ru from "../../../i18n/ru.json";

import { DatePicker } from "./date-picker";

function renderPicker(props: Partial<React.ComponentProps<typeof DatePicker>> = {}) {
  const onChange = vi.fn();
  const utils = render(
    <NextIntlClientProvider locale="ru" messages={ru}>
      <DatePicker value={undefined} onChange={onChange} {...props} />
    </NextIntlClientProvider>,
  );
  return { ...utils, onChange };
}

describe("DatePicker (Phase 6)", () => {
  it("показывает placeholder когда value пустое", () => {
    renderPicker({ placeholder: "Выбери дату" });
    expect(screen.getByRole("button", { name: /выбери дату/i })).toBeInTheDocument();
  });

  it("форматирует value как DD.MM.YYYY", () => {
    renderPicker({ value: "2019-08-12" });
    // Триггер — единственная button до открытия popover.
    const trigger = screen.getByRole("button");
    expect(trigger).toHaveTextContent("12.08.2019");
  });

  it("открывает popover и пишет ISO при клике по дню", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPicker({ value: "2026-05-14" });
    // Trigger — единственная button до открытия popover.
    await user.click(screen.getByRole("button"));
    // react-day-picker v9 ставит aria-label вида "среда, 20 мая 2026 г."
    const day20 = screen.getByRole("button", { name: /20 мая 2026/ });
    await user.click(day20);
    expect(onChange).toHaveBeenCalledWith("2026-05-20");
  });

  it("«Очистить» вызывает onChange(undefined)", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPicker({ value: "2026-05-14" });
    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("button", { name: /^очистить$/i }));
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it("«Сегодня» — onChange сегодняшней даты", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPicker({ value: undefined });
    await user.click(screen.getByRole("button"));
    await user.click(screen.getByRole("button", { name: /^сегодня$/i }));
    const today = new Date();
    const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    expect(onChange).toHaveBeenCalledWith(iso);
  });

  it("дни после `max` disabled", async () => {
    const user = userEvent.setup();
    // value заякорит view в мае 2026; max = 2026-05-14 → дни 15+ disabled.
    renderPicker({ value: "2026-05-14", max: new Date("2026-05-14") });
    await user.click(screen.getByRole("button"));
    const day25 = screen.getByRole("button", { name: /25 мая 2026/ });
    expect(day25).toBeDisabled();
  });
});
