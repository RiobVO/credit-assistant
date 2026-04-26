// CA-040 smoke: ключевые null-семантические ветки CA-033 / CA-034.
// Цель — поймать регресс «случайно вернули 0 там, где смысл null».
import { describe, it, expect } from "vitest";

import {
  classifyDscrRisk,
  computeCagrPct,
  computeDscr,
  computeMarginPct,
} from "./finance";

describe("computeDscr (CA-033 null-семантика)", () => {
  it("null при отсутствии аннуитета (monthlyPayment null/<=0)", () => {
    expect(computeDscr(10_000_000, null)).toBeNull();
    expect(computeDscr(10_000_000, 0)).toBeNull();
    expect(computeDscr(10_000_000, -1)).toBeNull();
  });

  it("null при отсутствии финансового отчёта (netProfit null)", () => {
    expect(computeDscr(null, 1_000_000)).toBeNull();
  });

  it("0 при явной нулевой прибыли — это red-flag, не «нет данных»", () => {
    expect(computeDscr(0, 1_000_000)).toBe(0);
  });

  it("отрицательный DSCR при убытке — валидный сигнал, не null", () => {
    expect(computeDscr(-12_000_000, 1_000_000)).toBe(-1);
  });

  it("обычный расчёт: годовая прибыль / (мес. платёж × 12)", () => {
    expect(computeDscr(24_000_000, 1_000_000)).toBe(2);
  });
});

describe("classifyDscrRisk (CA-033 четыре ветки)", () => {
  it("null → neutral «Недостаточно данных»", () => {
    expect(classifyDscrRisk(null)).toEqual({
      label: "Недостаточно данных",
      tone: "neutral",
    });
  });

  it("≥ 1.5 → success", () => {
    expect(classifyDscrRisk(1.5).tone).toBe("success");
    expect(classifyDscrRisk(2).tone).toBe("success");
  });

  it("1.25 ≤ x < 1.5 → warning", () => {
    expect(classifyDscrRisk(1.25).tone).toBe("warning");
    expect(classifyDscrRisk(1.49).tone).toBe("warning");
  });

  it("< 1.25 → danger (включая 0 и отрицательные)", () => {
    expect(classifyDscrRisk(1.24).tone).toBe("danger");
    expect(classifyDscrRisk(0).tone).toBe("danger");
    expect(classifyDscrRisk(-0.5).tone).toBe("danger");
  });
});

describe("computeMarginPct (CA-034 null-семантика)", () => {
  it("null при нулевой/отрицательной выручке (деление ≠ «0% маржи»)", () => {
    expect(computeMarginPct(100, 0)).toBeNull();
    expect(computeMarginPct(100, -1)).toBeNull();
  });

  it("отрицательная маржа при убытке — валидное число", () => {
    expect(computeMarginPct(-1000, 10_000)).toBe(-10);
  });

  it("обычный расчёт в процентах", () => {
    expect(computeMarginPct(1500, 10_000)).toBe(15);
  });
});

describe("computeCagrPct (CA-034 null-семантика)", () => {
  it("null при start <= 0 — нельзя посчитать рост от нуля", () => {
    expect(computeCagrPct(0, 100, 2)).toBeNull();
    expect(computeCagrPct(-10, 100, 2)).toBeNull();
  });

  it("null при years <= 0", () => {
    expect(computeCagrPct(100, 200, 0)).toBeNull();
    expect(computeCagrPct(100, 200, -1)).toBeNull();
  });

  it("2x за 2 года ≈ 41.42%", () => {
    const v = computeCagrPct(100, 200, 2);
    expect(v).not.toBeNull();
    expect(v!).toBeCloseTo(41.42, 1);
  });
});
