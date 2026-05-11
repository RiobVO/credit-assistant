// CA-039: pre-warning для свеженазначенного директора.
import { describe, it, expect } from "vitest";

import { isRecentDirectorAppointment } from "./step-1-borrower";

const NOW = new Date("2026-05-12T12:00:00Z");

describe("isRecentDirectorAppointment (CA-039)", () => {
  it("false при пустом значении", () => {
    expect(isRecentDirectorAppointment(undefined, 90, NOW)).toBe(false);
    expect(isRecentDirectorAppointment("", 90, NOW)).toBe(false);
  });

  it("false при невалидной дате", () => {
    expect(isRecentDirectorAppointment("2026-13-99", 90, NOW)).toBe(false);
    expect(isRecentDirectorAppointment("abc", 90, NOW)).toBe(false);
  });

  it("true при назначении 30 дней назад", () => {
    expect(isRecentDirectorAppointment("2026-04-12", 90, NOW)).toBe(true);
  });

  it("true при назначении сегодня (0 дней)", () => {
    expect(isRecentDirectorAppointment("2026-05-12", 90, NOW)).toBe(true);
  });

  it("граница 89/90 — порог exclusive", () => {
    // NOW=2026-05-12; «2026-02-11» = 90 дней назад → false;
    // «2026-02-12» = 89 дней назад → true. Порог diff<90 (exclusive).
    expect(isRecentDirectorAppointment("2026-02-11", 90, NOW)).toBe(false);
    expect(isRecentDirectorAppointment("2026-02-12", 90, NOW)).toBe(true);
  });

  it("false при назначении >90 дней назад", () => {
    expect(isRecentDirectorAppointment("2025-01-01", 90, NOW)).toBe(false);
  });

  it("false при будущей дате (нет смысла)", () => {
    expect(isRecentDirectorAppointment("2027-01-01", 90, NOW)).toBe(false);
  });
});
