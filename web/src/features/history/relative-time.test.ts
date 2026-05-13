import { describe, expect, it } from "vitest";

import { formatRelativeTime, isFreshTime } from "./relative-time";

const now = new Date("2026-05-13T18:00:00");

describe("formatRelativeTime", () => {
  it("returns just_now for < 1 minute", () => {
    const iso = new Date(now.getTime() - 30 * 1000).toISOString();
    expect(formatRelativeTime(iso, now)).toEqual({ key: "rel_just_now" });
  });

  it("returns minutes for < 1 hour same day", () => {
    const iso = new Date(now.getTime() - 14 * 60 * 1000).toISOString();
    expect(formatRelativeTime(iso, now)).toEqual({
      key: "rel_minutes",
      values: { n: 14 },
    });
  });

  it("returns hours for ≥ 1 hour same day", () => {
    const iso = new Date(now.getTime() - 5 * 3600 * 1000).toISOString();
    expect(formatRelativeTime(iso, now)).toEqual({
      key: "rel_hours",
      values: { n: 5 },
    });
  });

  it("returns yesterday for previous calendar day even if < 24h diff", () => {
    // 23:00 предыдущего дня, диф = 19ч — но это yesterday по календарю.
    const iso = new Date("2026-05-12T23:00:00").toISOString();
    expect(formatRelativeTime(iso, new Date("2026-05-13T01:00:00"))).toEqual({
      key: "rel_yesterday",
      values: { time: "23:00" },
    });
  });

  it("returns days for 2-6 calendar days ago", () => {
    const iso = new Date("2026-05-10T12:00:00").toISOString();
    expect(formatRelativeTime(iso, now)).toEqual({
      key: "rel_days",
      values: { n: 3 },
    });
  });

  it("returns null for ≥ 7 days", () => {
    const iso = new Date("2026-05-01T12:00:00").toISOString();
    expect(formatRelativeTime(iso, now)).toBeNull();
  });

  it("returns null for future dates", () => {
    const iso = new Date(now.getTime() + 60 * 1000).toISOString();
    expect(formatRelativeTime(iso, now)).toBeNull();
  });
});

describe("isFreshTime", () => {
  it("is fresh today", () => {
    expect(isFreshTime(new Date(now.getTime() - 3600 * 1000).toISOString(), now)).toBe(true);
  });
  it("is fresh yesterday", () => {
    expect(isFreshTime("2026-05-12T23:00:00", new Date("2026-05-13T01:00:00"))).toBe(true);
  });
  it("is not fresh 2 days ago", () => {
    expect(isFreshTime("2026-05-11T12:00:00", now)).toBe(false);
  });
  it("is not fresh in the future", () => {
    expect(isFreshTime(new Date(now.getTime() + 1000).toISOString(), now)).toBe(false);
  });
});
