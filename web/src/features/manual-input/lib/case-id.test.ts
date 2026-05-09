// CA-DS18 Level 1: тесты formatCaseId — deterministic из draft.id.

import { describe, expect, it } from "vitest";

import { formatCaseId } from "./case-id";

describe("formatCaseId", () => {
  it("returns null when draftId is null", () => {
    expect(formatCaseId(null)).toBeNull();
  });

  it("returns null when draftId is empty string", () => {
    expect(formatCaseId("")).toBeNull();
  });

  it("formats UUID into BR-YYYY-XXXX with current year", () => {
    const fixed = new Date("2026-05-16T10:00:00Z");
    const id = formatCaseId("a3f71b2c-9d8e-4567-abcd-ef0123456789", fixed);
    expect(id).toBe("BR-2026-A3F7");
  });

  it("strips dashes from UUID before slicing", () => {
    // Если бы не strip — `slice(0,4)` вернул бы "a3f7" (4 hex), но с UUID
    // структурой `xxxxxxxx-xxxx-...` дефис на 9-й позиции этого случая
    // не задевает. Тест защищает от регрессии при «коротких» UUID.
    const fixed = new Date("2026-01-01T00:00:00Z");
    const id = formatCaseId("ab-cd-ef-1234567890", fixed);
    expect(id).toBe("BR-2026-ABCD");
  });

  it("uppercases hex prefix", () => {
    const fixed = new Date("2026-01-01T00:00:00Z");
    const id = formatCaseId("deadbeef-0000-0000-0000-000000000000", fixed);
    expect(id).toBe("BR-2026-DEAD");
  });

  it("returns null when draftId has fewer than 4 hex chars", () => {
    // Гипотетический degraded draft.id — backend не должен такое возвращать,
    // но мы не падаем, а возвращаем null (UI покажет «—»).
    const fixed = new Date("2026-01-01T00:00:00Z");
    expect(formatCaseId("ab", fixed)).toBeNull();
    expect(formatCaseId("a-b", fixed)).toBeNull();
  });

  it("uses current year by default", () => {
    const id = formatCaseId("a3f71b2c-9d8e-4567-abcd-ef0123456789");
    expect(id).toMatch(/^BR-\d{4}-A3F7$/);
  });

  it("is deterministic — same input always yields same output", () => {
    const fixed = new Date("2026-05-16T10:00:00Z");
    const draftId = "12345678-90ab-cdef-1234-567890abcdef";
    expect(formatCaseId(draftId, fixed)).toBe(formatCaseId(draftId, fixed));
  });
});
