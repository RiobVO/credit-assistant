// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";

import ru from "../i18n/ru.json";
import { GlobalTopbar } from "./global-topbar";

afterEach(cleanup);

function wrap(ui: React.ReactElement) {
  return (
    <NextIntlClientProvider locale="ru" messages={ru}>
      {ui}
    </NextIntlClientProvider>
  );
}

describe("GlobalTopbar", () => {
  it("renders breadcrumbs", () => {
    render(
      wrap(
        <GlobalTopbar
          crumbs={[
            { label: "История", href: "/history" },
            { label: "ИНН 201308534", current: true },
          ]}
        />,
      ),
    );
    expect(screen.getByText("История")).toBeTruthy();
    expect(screen.getByText("ИНН 201308534")).toBeTruthy();
  });

  it("opens command palette on Cmd+K", () => {
    const onSearchOpen = vi.fn();
    render(wrap(<GlobalTopbar crumbs={[]} onSearchOpen={onSearchOpen} />));
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(onSearchOpen).toHaveBeenCalled();
  });
});
