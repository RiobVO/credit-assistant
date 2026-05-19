// CA-DS22: RTL-тесты на keyboard nav в CustomDropdown.
//
// Покрываем:
//   * ArrowDown открывает + highlight 0 → первая опция активна
//   * ArrowDown / ArrowUp двигают highlight по опциям (clamp к границам)
//   * Home / End → первая / последняя опция
//   * Enter on closed → opens; Enter on open → commits highlighted
//   * Space on closed → opens
//   * Escape закрывает без выбора
//   * aria-activedescendant ссылается на корректный option id
//   * mouse-нав остаётся работать (regression check)

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { CustomDropdown, type DropdownOption } from "./custom-dropdown";

const OPTIONS: DropdownOption<number>[] = [
  { value: 6, label: "6 месяцев" },
  { value: 12, label: "12 месяцев" },
  { value: 24, label: "24 месяца" },
  { value: 36, label: "36 месяцев" },
];

function renderDropdown(initial: number = 12) {
  let lastValue = initial;
  function Harness() {
    const [value, setValue] = useState(initial);
    return (
      <CustomDropdown<number>
        value={value}
        onChange={(v) => {
          setValue(v);
          lastValue = v;
        }}
        options={OPTIONS}
      />
    );
  }
  const utils = render(<Harness />);
  return {
    ...utils,
    button: utils.container.querySelector("button")!,
    getValue: () => lastValue,
  };
}

describe("CustomDropdown keyboard nav (CA-DS22)", () => {
  it("ArrowDown на closed → открывает + highlight = currently-selected", async () => {
    const { button } = renderDropdown(12); // value=12 → idx 1
    fireEvent.keyDown(button, { key: "ArrowDown" });
    const listbox = await screen.findByRole("listbox");
    expect(listbox).toBeInTheDocument();
    const options = screen.getAllByRole("option");
    // aria-selected стабильно на selected option (idx 1 для value=12).
    expect(options[1].getAttribute("aria-selected")).toBe("true");
    // Initial highlight = selected (CA-DS22 design — keyboard nav начинает там
    // где пользователь сейчас, не с idx 0). aria-activedescendant отражает highlight.
    // setHighlight выполняется через setTimeout(0) (см. CustomDropdown комментарий
    // про react-hooks/set-state-in-effect) — ждём через waitFor чтобы CI с
    // быстрым tick'ом не падал на race condition.
    await waitFor(() => {
      expect(button.getAttribute("aria-activedescendant")).toBe(options[1].id);
    });
  });

  it("Enter на closed → открывает (без commit)", async () => {
    const { button, getValue } = renderDropdown();
    fireEvent.keyDown(button, { key: "Enter" });
    await screen.findByRole("listbox");
    expect(getValue()).toBe(12); // не изменился
  });

  it("Space на closed → открывает", async () => {
    const { button } = renderDropdown();
    fireEvent.keyDown(button, { key: " " });
    expect(await screen.findByRole("listbox")).toBeInTheDocument();
  });

  it("ArrowDown открывает + ArrowDown × 1 + Enter → следующая опция (idx 2 → value=24)", async () => {
    const { button, getValue } = renderDropdown(12); // initial highlight = idx 1
    fireEvent.keyDown(button, { key: "ArrowDown" }); // opens, highlight stays 1
    await screen.findByRole("listbox");
    fireEvent.keyDown(button, { key: "ArrowDown" }); // highlight 1 → 2
    fireEvent.keyDown(button, { key: "Enter" }); // commit idx 2 → 24
    expect(getValue()).toBe(24);
    // После commit dropdown закрывается.
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  it("ArrowDown clamp к последней опции", async () => {
    const { button } = renderDropdown();
    fireEvent.keyDown(button, { key: "ArrowDown" }); // open + idx 0
    await screen.findByRole("listbox");
    for (let i = 0; i < 10; i++) {
      fireEvent.keyDown(button, { key: "ArrowDown" });
    }
    const options = screen.getAllByRole("option");
    expect(button.getAttribute("aria-activedescendant")).toBe(
      options[options.length - 1].id,
    );
  });

  it("ArrowUp clamp к первой опции (≥0)", async () => {
    const { button } = renderDropdown();
    fireEvent.keyDown(button, { key: "ArrowDown" }); // idx 0
    await screen.findByRole("listbox");
    for (let i = 0; i < 5; i++) {
      fireEvent.keyDown(button, { key: "ArrowUp" });
    }
    const options = screen.getAllByRole("option");
    expect(button.getAttribute("aria-activedescendant")).toBe(options[0].id);
  });

  it("Home → highlight 0", async () => {
    const { button } = renderDropdown();
    fireEvent.keyDown(button, { key: "ArrowDown" }); // open
    await screen.findByRole("listbox");
    fireEvent.keyDown(button, { key: "ArrowDown" });
    fireEvent.keyDown(button, { key: "ArrowDown" });
    fireEvent.keyDown(button, { key: "Home" });
    const options = screen.getAllByRole("option");
    expect(button.getAttribute("aria-activedescendant")).toBe(options[0].id);
  });

  it("End → highlight last", async () => {
    const { button } = renderDropdown();
    fireEvent.keyDown(button, { key: "ArrowDown" }); // open
    await screen.findByRole("listbox");
    fireEvent.keyDown(button, { key: "End" });
    const options = screen.getAllByRole("option");
    expect(button.getAttribute("aria-activedescendant")).toBe(
      options[options.length - 1].id,
    );
  });

  it("Escape закрывает без выбора", async () => {
    const { button, getValue } = renderDropdown();
    fireEvent.keyDown(button, { key: "ArrowDown" });
    await screen.findByRole("listbox");
    fireEvent.keyDown(button, { key: "ArrowDown" });
    fireEvent.keyDown(button, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
    expect(getValue()).toBe(12); // не изменился
  });

  it("mouse click остаётся работать (regression)", async () => {
    const { button, getValue } = renderDropdown();
    fireEvent.click(button);
    const opt = await screen.findByText("36 месяцев");
    fireEvent.click(opt);
    expect(getValue()).toBe(36);
  });

  it("на open initial highlight = индекс current value (не 0)", async () => {
    const { button } = renderDropdown(24); // value=24 → idx 2
    fireEvent.keyDown(button, { key: "ArrowDown" });
    await screen.findByRole("listbox");
    const options = screen.getAllByRole("option");
    // First ArrowDown открывает + ставит highlight на selected (24 → idx 2).
    // Дизайн-инвариант: keyboard nav начинает с currently selected, а не с 0.
    // setHighlight идёт через setTimeout(0) (макротаск) — без waitFor full-run
    // vitest race-condition'ит при нагруженной queue (single-file успевает).
    await waitFor(() => {
      expect(button.getAttribute("aria-activedescendant")).toBe(options[2].id);
    });
  });
});
