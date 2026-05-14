// Phase 2 (DS-PHASE-2): unit-тесты pure хелперов result-card.
import { describe, expect, it } from "vitest";

import {
  formatRevenueMillions,
  formatRevenueShort,
  formatYoy,
  parseIsoMonth,
  splitBusinessAge,
} from "./format";

describe("formatRevenueShort (ru)", () => {
  it("млрд: ≥1B → «4,12 млрд сум»", () => {
    expect(formatRevenueShort("4120000000", "ru")).toBe("4,12 млрд сум");
  });

  it("млн: 1M..1B → «560 млн сум»", () => {
    expect(formatRevenueShort("560000000", "ru")).toBe("560 млн сум");
  });

  it("null / пустая строка → null", () => {
    expect(formatRevenueShort(null, "ru")).toBeNull();
    expect(formatRevenueShort("", "ru")).toBeNull();
  });

  it("zero → null (нечего показывать)", () => {
    expect(formatRevenueShort("0", "ru")).toBeNull();
  });
});

describe("formatRevenueShort (uz)", () => {
  it("mlrd: ≥1B → «4,12 mlrd soʻm» с U+02BB", () => {
    expect(formatRevenueShort("4120000000", "uz")).toBe(`4,12 mlrd soʻm`);
  });

  it("mln: 1M..1B → «560 mln soʻm»", () => {
    expect(formatRevenueShort("560000000", "uz")).toBe(`560 mln soʻm`);
  });
});

describe("formatRevenueMillions", () => {
  it("Decimal → миллионы как целое", () => {
    expect(formatRevenueMillions("560000000")).toBe("560");
  });

  it("округляет 5.4M → 5", () => {
    expect(formatRevenueMillions("5400000")).toBe("5");
  });

  it("non-finite → «—»", () => {
    expect(formatRevenueMillions("abc")).toBe("—");
  });
});

describe("parseIsoMonth", () => {
  it("YYYY-MM валидно", () => {
    expect(parseIsoMonth("2026-05")).toEqual({ monthIndex: 5, yearShort: "26" });
  });

  it("mal-format → null", () => {
    expect(parseIsoMonth("2026/05")).toBeNull();
    expect(parseIsoMonth("26-05")).toBeNull();
    expect(parseIsoMonth("2026-13")).toBeNull();
  });
});

describe("formatYoy", () => {
  it("положительный с +", () => {
    expect(formatYoy(18.4)).toBe("+18,4%");
  });

  it("отрицательный с −", () => {
    expect(formatYoy(-5.2)).toBe("−5,2%");
  });

  it("ноль без знака", () => {
    expect(formatYoy(0)).toBe("0,0%");
  });

  it("null → «—»", () => {
    expect(formatYoy(null)).toBe("—");
  });
});

describe("splitBusinessAge", () => {
  it("87 мес → 7 лет 3 мес", () => {
    expect(splitBusinessAge(87)).toEqual({ years: 7, months: 3 });
  });

  it("12 мес → 1 год 0 мес", () => {
    expect(splitBusinessAge(12)).toEqual({ years: 1, months: 0 });
  });

  it("0 мес → 0 / 0", () => {
    expect(splitBusinessAge(0)).toEqual({ years: 0, months: 0 });
  });
});
