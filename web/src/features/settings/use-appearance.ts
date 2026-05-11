"use client";

// Appearance state — client-only, persist в localStorage, прокидывает CSS-переменные
// на <html data-density> / <html data-font-scale> / <html data-reduced-motion>.
// `useReducedMotion` (web/src/lib/use-reduced-motion.ts) уже читает OS-preference;
// здесь добавляем явный override от пользователя.

import { useEffect, useState } from "react";

const LS_PREFIX = "ca:settings";

export type Theme = "light" | "dark" | "system";
export type Density = "compact" | "standard";
export type FontScale = "s" | "m" | "l";

type State = {
  theme: Theme;
  density: Density;
  fontScale: FontScale;
  reducedMotion: boolean;
};

const DEFAULT_STATE: State = {
  theme: "light",
  density: "compact",
  fontScale: "m",
  reducedMotion: false,
};

function readLsString(key: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(`${LS_PREFIX}:${key}`);
    return raw === null ? fallback : raw;
  } catch {
    return fallback;
  }
}

function writeLsString(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${LS_PREFIX}:${key}`, value);
  } catch {
    // Storage full / disabled — игнорим, в памяти state живёт.
  }
}

function readTheme(): Theme {
  const raw = readLsString("theme", DEFAULT_STATE.theme);
  return raw === "dark" || raw === "system" ? (raw as Theme) : "light";
}
function readDensity(): Density {
  const raw = readLsString("density", DEFAULT_STATE.density);
  return raw === "standard" ? "standard" : "compact";
}
function readFontScale(): FontScale {
  const raw = readLsString("fontScale", DEFAULT_STATE.fontScale);
  return raw === "s" || raw === "l" ? (raw as FontScale) : "m";
}
function readReducedMotion(): boolean {
  return readLsString("reducedMotion", "false") === "true";
}

function applyToDocument(state: State): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.theme = state.theme;
  root.dataset.density = state.density;
  root.dataset.fontScale = state.fontScale;
  root.dataset.reducedMotion = state.reducedMotion ? "true" : "false";
}

export function useAppearance() {
  // Lazy initial state: читаем из LS только на client (SSR fallback = defaults).
  const [state, setState] = useState<State>(() => ({
    theme: readTheme(),
    density: readDensity(),
    fontScale: readFontScale(),
    reducedMotion: readReducedMotion(),
  }));

  // Sync to <html> attributes at mount + on any change.
  useEffect(() => {
    applyToDocument(state);
  }, [state]);

  // System mode live sync: когда theme === "system", слушаем OS preference и
  // ре-проставляем data-theme на root. CSS @media (prefers-color-scheme: dark)
  // [data-theme="system"] {} обслуживает первый paint; listener нужен для
  // тех случаев когда user меняет OS-тему пока приложение открыто.
  useEffect(() => {
    if (typeof window === "undefined" || state.theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      // data-theme остаётся "system" — атрибут проставлен через applyToDocument;
      // listener только триггерит React-rerender зависимых компонентов через
      // принудительный re-apply (на случай если useEffect выше уже отработал).
      applyToDocument({ ...state });
    };
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [state]);

  return {
    state,
    setTheme: (theme: Theme) => {
      writeLsString("theme", theme);
      setState((s) => ({ ...s, theme }));
    },
    setDensity: (density: Density) => {
      writeLsString("density", density);
      setState((s) => ({ ...s, density }));
    },
    setFontScale: (fontScale: FontScale) => {
      writeLsString("fontScale", fontScale);
      setState((s) => ({ ...s, fontScale }));
    },
    setReducedMotion: (reducedMotion: boolean) => {
      writeLsString("reducedMotion", reducedMotion ? "true" : "false");
      setState((s) => ({ ...s, reducedMotion }));
    },
  };
}
