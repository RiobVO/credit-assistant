// RTL для AppearanceSection — 3 theme swatches activeable, click меняет
// useAppearance state и data-theme на <html>.

import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ru from "../../i18n/ru.json";
import { AppearanceSection } from "./appearance-section";

function renderSection() {
  return render(
    <NextIntlClientProvider locale="ru" messages={ru}>
      <AppearanceSection />
    </NextIntlClientProvider>,
  );
}

describe("AppearanceSection — theme swatches", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      media: "(prefers-color-scheme: dark)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("рендерит 3 swatch-кнопки (Светлая / Тёмная / Системная)", () => {
    renderSection();
    expect(screen.getByRole("button", { name: /Светлая/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Тёмная/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Системная/i }),
    ).toBeInTheDocument();
  });

  it("все 3 swatch активны (ни одна не disabled)", () => {
    renderSection();
    const light = screen.getByRole("button", { name: /Светлая/i });
    const dark = screen.getByRole("button", { name: /Тёмная/i });
    const system = screen.getByRole("button", { name: /Системная/i });
    expect(light).not.toBeDisabled();
    expect(dark).not.toBeDisabled();
    expect(system).not.toBeDisabled();
  });

  it("по умолчанию active — Светлая (aria-pressed=true)", () => {
    renderSection();
    expect(
      screen.getByRole("button", { name: /Светлая/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Тёмная/i })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("click на Тёмную — aria-pressed=true + data-theme=dark на <html>", () => {
    renderSection();
    fireEvent.click(screen.getByRole("button", { name: /Тёмная/i }));
    expect(screen.getByRole("button", { name: /Тёмная/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("click на Системную — data-theme=system на <html>", () => {
    renderSection();
    fireEvent.click(screen.getByRole("button", { name: /Системная/i }));
    expect(document.documentElement.dataset.theme).toBe("system");
  });

  it("переключение dark → light возвращает data-theme=light", () => {
    renderSection();
    fireEvent.click(screen.getByRole("button", { name: /Тёмная/i }));
    fireEvent.click(screen.getByRole("button", { name: /Светлая/i }));
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});
