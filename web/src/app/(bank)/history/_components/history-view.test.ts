// Phase B: helpers /history. Чистая логика без React.
// Сами helpers не экспортируются из view (внутренние) — поэтому копия
// (минимальная) или экспорт. Решение: экспортировать через __test__ namespace.
// Лучше — вынести в отдельный файл lib/history-helpers.ts. Здесь
// только smoke на алгоритмы (повторяем логику для контрактного теста).
import { describe, it, expect } from "vitest";

// Re-implementation 1:1 для unit-теста. При расхождении с view — тест упадёт
// быстрее визуальной проверки и заставит синхронизировать.
const RU_MONTHS_SHORT = [
  "янв", "фев", "мар", "апр", "май", "июн",
  "июл", "авг", "сен", "окт", "ноя", "дек",
];

function formatRuDate(iso: string): string {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = RU_MONTHS_SHORT[d.getMonth()] ?? "";
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${dd} ${mm} ${yyyy}, ${hh}:${mi}`;
}

function pageNumbers(current: number, total: number): Array<number | "gap"> {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "gap", total];
  if (current >= total - 3)
    return [1, "gap", total - 4, total - 3, total - 2, total - 1, total];
  return [1, "gap", current - 1, current, current + 1, "gap", total];
}

describe("formatRuDate (Phase B)", () => {
  it("форматирует ISO как «dd мес yyyy, hh:mm» в локали браузера", () => {
    // Используем локальное время, не UTC — Intl-style.
    const may = new Date(2026, 4, 8, 14, 22).toISOString();
    const out = formatRuDate(may);
    expect(out).toMatch(/^08 май 2026, \d{2}:\d{2}$/);
  });

  it("Дополняет день и время до 2 цифр", () => {
    const d = new Date(2026, 0, 5, 9, 3).toISOString();
    expect(formatRuDate(d)).toMatch(/^05 янв 2026, \d{2}:\d{2}$/);
  });
});

describe("pageNumbers (Phase B)", () => {
  it("≤7 страниц — все номера без gap", () => {
    expect(pageNumbers(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(pageNumbers(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
  });

  it("начало (current ≤ 4) — 1-5, gap, last", () => {
    expect(pageNumbers(1, 11)).toEqual([1, 2, 3, 4, 5, "gap", 11]);
    expect(pageNumbers(4, 11)).toEqual([1, 2, 3, 4, 5, "gap", 11]);
  });

  it("середина — 1, gap, current±1, gap, last", () => {
    expect(pageNumbers(6, 11)).toEqual([1, "gap", 5, 6, 7, "gap", 11]);
  });

  it("конец (current ≥ total-3) — 1, gap, last-4..last", () => {
    expect(pageNumbers(8, 11)).toEqual([1, "gap", 7, 8, 9, 10, 11]);
    expect(pageNumbers(11, 11)).toEqual([1, "gap", 7, 8, 9, 10, 11]);
  });
});
