// Unit-тесты useAppearance — theme/density/font/motion persisted в localStorage,
// applyToDocument проставляет data-атрибуты на <html>, system mode подписывается
// на matchMedia change.

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAppearance } from "./use-appearance";

type MqlListener = (e: MediaQueryListEvent) => void;

function setupMatchMedia(initialMatches: boolean = false) {
  const listeners = new Set<MqlListener>();
  const mql = {
    matches: initialMatches,
    media: "(prefers-color-scheme: dark)",
    onchange: null,
    addEventListener: vi.fn((_: string, cb: MqlListener) => {
      listeners.add(cb);
    }),
    removeEventListener: vi.fn((_: string, cb: MqlListener) => {
      listeners.delete(cb);
    }),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList & { matches: boolean };

  window.matchMedia = vi.fn().mockReturnValue(mql);
  return {
    mql,
    fire: (matches: boolean) => {
      (mql as { matches: boolean }).matches = matches;
      listeners.forEach((cb) =>
        cb({ matches } as MediaQueryListEvent),
      );
    },
  };
}

describe("useAppearance", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    document.documentElement.removeAttribute("data-density");
    document.documentElement.removeAttribute("data-font-scale");
    document.documentElement.removeAttribute("data-reduced-motion");
    setupMatchMedia(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("default state — light / compact / m / no reduced motion", () => {
    const { result } = renderHook(() => useAppearance());
    expect(result.current.state).toEqual({
      theme: "light",
      density: "compact",
      fontScale: "m",
      reducedMotion: false,
    });
  });

  it("applyToDocument проставляет все 4 data-атрибута на <html>", () => {
    renderHook(() => useAppearance());
    const root = document.documentElement;
    expect(root.dataset.theme).toBe("light");
    expect(root.dataset.density).toBe("compact");
    expect(root.dataset.fontScale).toBe("m");
    expect(root.dataset.reducedMotion).toBe("false");
  });

  it("setTheme dark — persists в LS + проставляет data-theme=dark", () => {
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setTheme("dark"));
    expect(result.current.state.theme).toBe("dark");
    expect(window.localStorage.getItem("ca:settings:theme")).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("setTheme system — persists + проставляет data-theme=system", () => {
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setTheme("system"));
    expect(result.current.state.theme).toBe("system");
    expect(window.localStorage.getItem("ca:settings:theme")).toBe("system");
    expect(document.documentElement.dataset.theme).toBe("system");
  });

  it("на mount читает theme из LS (dark)", () => {
    window.localStorage.setItem("ca:settings:theme", "dark");
    const { result } = renderHook(() => useAppearance());
    expect(result.current.state.theme).toBe("dark");
  });

  it("invalid LS value падает на light", () => {
    window.localStorage.setItem("ca:settings:theme", "invalid");
    const { result } = renderHook(() => useAppearance());
    expect(result.current.state.theme).toBe("light");
  });

  it("setDensity standard — persists + data-density=standard", () => {
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setDensity("standard"));
    expect(window.localStorage.getItem("ca:settings:density")).toBe("standard");
    expect(document.documentElement.dataset.density).toBe("standard");
  });

  it("setFontScale l — persists + data-font-scale=l", () => {
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setFontScale("l"));
    expect(window.localStorage.getItem("ca:settings:fontScale")).toBe("l");
    expect(document.documentElement.dataset.fontScale).toBe("l");
  });

  it("setReducedMotion true — persists + data-reduced-motion=true", () => {
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setReducedMotion(true));
    expect(window.localStorage.getItem("ca:settings:reducedMotion")).toBe(
      "true",
    );
    expect(document.documentElement.dataset.reducedMotion).toBe("true");
  });

  it("system mode подписывается на matchMedia change", () => {
    const { mql } = setupMatchMedia(false);
    const { result } = renderHook(() => useAppearance());
    act(() => result.current.setTheme("system"));
    expect(mql.addEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });

  it("при unmount матчмедиа listener удаляется (no leak)", () => {
    const { mql } = setupMatchMedia(false);
    const { result, unmount } = renderHook(() => useAppearance());
    act(() => result.current.setTheme("system"));
    unmount();
    expect(mql.removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });

  it("при theme !== system listener не вешается", () => {
    const { mql } = setupMatchMedia(false);
    renderHook(() => useAppearance());
    expect(mql.addEventListener).not.toHaveBeenCalled();
  });
});
