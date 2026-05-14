// T0.4 B4: unit-тесты formatBigUzs locale-suffix.
// Локализация — silent регрессии (no compile-time guarantee), поэтому
// прибиваем по одному кейсу на scale × locale + non-finite fallback.
import { describe, expect, it } from "vitest";

import { formatBigUzs } from "./format";

const NBSP = " ";

describe("formatBigUzs (ru)", () => {
  it("≥1B → «N,N млрд сум» с NBSP", () => {
    expect(formatBigUzs(4_120_000_000, "ru")).toBe(`4,1${NBSP}млрд${NBSP}сум`);
  });

  it("1M..1B → «N,N млн сум»", () => {
    expect(formatBigUzs(560_000_000, "ru")).toBe(`560,0${NBSP}млн${NBSP}сум`);
  });

  it("1K..1M → «N,N тыс сум»", () => {
    expect(formatBigUzs(45_000, "ru")).toBe(`45,0${NBSP}тыс${NBSP}сум`);
  });

  it("<1K → «N сум» без дробной части", () => {
    expect(formatBigUzs(420, "ru")).toBe(`420${NBSP}сум`);
  });
});

describe("formatBigUzs (uz)", () => {
  it("≥1B → «N,N mlrd soʻm» с U+02BB", () => {
    expect(formatBigUzs(4_120_000_000, "uz")).toBe(`4,1${NBSP}mlrd${NBSP}soʻm`);
  });

  it("1M..1B → «N,N mln soʻm»", () => {
    expect(formatBigUzs(560_000_000, "uz")).toBe(`560,0${NBSP}mln${NBSP}soʻm`);
  });

  it("1K..1M → «N,N ming soʻm»", () => {
    expect(formatBigUzs(45_000, "uz")).toBe(`45,0${NBSP}ming${NBSP}soʻm`);
  });

  it("<1K → «N soʻm»", () => {
    expect(formatBigUzs(420, "uz")).toBe(`420${NBSP}soʻm`);
  });
});

describe("formatBigUzs non-finite", () => {
  it("NaN → «—»", () => {
    expect(formatBigUzs(NaN, "ru")).toBe("—");
    expect(formatBigUzs(NaN, "uz")).toBe("—");
  });

  it("Infinity → «—»", () => {
    expect(formatBigUzs(Infinity, "ru")).toBe("—");
  });
});
