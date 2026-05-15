import { describe, expect, it } from "vitest";

import type { BrandBusinessHours } from "@/lib/brand";

import { getHotlineStatus } from "./business-hours";

const TASHKENT_OFFSET = 5;

function tashkentMoment(
  year: number,
  monthIdx0: number,
  day: number,
  hourLocal: number,
  minuteLocal = 0,
): Date {
  return new Date(
    Date.UTC(year, monthIdx0, day, hourLocal - TASHKENT_OFFSET, minuteLocal),
  );
}

describe("getHotlineStatus", () => {
  it("midday weekday — open until 18", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 14));
    expect(status.open).toBe(true);
    if (status.open) expect(status.untilHour).toBe(18);
  });

  it("exactly 09:00 weekday — open (boundary inclusive)", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 9));
    expect(status.open).toBe(true);
  });

  it("exactly 18:00 weekday — closed (boundary exclusive)", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 18));
    expect(status.open).toBe(false);
    if (!status.open) expect(status.opensAtHour).toBe(9);
  });

  it("17:59 weekday — open", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 17, 59));
    expect(status.open).toBe(true);
  });

  it("08:30 weekday — closed (before open)", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 8, 30));
    expect(status.open).toBe(false);
  });

  it("Saturday midday — closed", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 16, 14));
    expect(status.open).toBe(false);
  });

  it("Sunday midday — closed", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 17, 14));
    expect(status.open).toBe(false);
  });

  // CA-DS7 — schedule из brand-config
  it("custom schedule из brand-config переопределяет default", () => {
    const schedule: BrandBusinessHours = {
      timezone: "Asia/Tashkent",
      weekdays: { start: "10:00", end: "20:00" },
    };
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 19), schedule);
    expect(status.open).toBe(true);
    if (status.open) expect(status.untilHour).toBe(20);
  });

  it("custom schedule с ранним закрытием — 17:00 уже closed", () => {
    const schedule: BrandBusinessHours = {
      timezone: "Asia/Tashkent",
      weekdays: { start: "09:00", end: "17:00" },
    };
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 17), schedule);
    expect(status.open).toBe(false);
    if (!status.open) expect(status.opensAtHour).toBe(9);
  });

  it("schedule=null → default fallback (09-18 Asia/Tashkent)", () => {
    const status = getHotlineStatus(tashkentMoment(2026, 4, 13, 10), null);
    expect(status.open).toBe(true);
    if (status.open) expect(status.untilHour).toBe(18);
  });
});
