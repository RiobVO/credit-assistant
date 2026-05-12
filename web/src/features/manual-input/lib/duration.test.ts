import { describe, it, expect } from "vitest";
import { formatBusinessAge } from "./duration";

describe("formatBusinessAge", () => {
  const now = new Date("2026-05-13");

  it("returns years + months", () => {
    expect(formatBusinessAge("2017-04-12", now)).toBe("9 лет 1 мес.");
  });
  it("handles 1-year edge case", () => {
    expect(formatBusinessAge("2025-05-13", now)).toBe("1 год");
  });
  it("returns null for invalid date", () => {
    expect(formatBusinessAge("abc", now)).toBeNull();
  });
  it("returns null for future date", () => {
    expect(formatBusinessAge("2030-01-01", now)).toBeNull();
  });
  it("returns just months when <1 year", () => {
    expect(formatBusinessAge("2026-01-13", now)).toBe("4 мес.");
  });
  it("pluralization: 2 года", () => {
    expect(formatBusinessAge("2024-05-13", now)).toBe("2 года");
  });
  it("pluralization: 11 лет (mod100 11-14 edge case)", () => {
    expect(formatBusinessAge("2015-05-13", now)).toBe("11 лет");
  });
  it("returns undefined-safe for empty input", () => {
    expect(formatBusinessAge(undefined, now)).toBeNull();
    expect(formatBusinessAge("", now)).toBeNull();
  });
});
