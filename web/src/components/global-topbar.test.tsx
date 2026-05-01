// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

import { GlobalTopbar } from "./global-topbar";

afterEach(cleanup);

describe("GlobalTopbar", () => {
  it("renders breadcrumbs", () => {
    render(
      <GlobalTopbar
        crumbs={[
          { label: "История", href: "/history" },
          { label: "ИНН 201308534", current: true },
        ]}
      />,
    );
    expect(screen.getByText("История")).toBeTruthy();
    expect(screen.getByText("ИНН 201308534")).toBeTruthy();
  });

  it("opens command palette on Cmd+K", () => {
    const onSearchOpen = vi.fn();
    render(<GlobalTopbar crumbs={[]} onSearchOpen={onSearchOpen} />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(onSearchOpen).toHaveBeenCalled();
  });
});
