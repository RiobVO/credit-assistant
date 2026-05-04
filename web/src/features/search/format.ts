// Phase 2 (DS-PHASE-2): хелперы форматирования для result-card.
// Цифры выручки → «4,12 млрд сум» / «560 млн сум»; ISO month → «Май 26»;
// business_age_months → {years, months} для i18n plural-template.

const MILLION = 1_000_000;
const BILLION = 1_000_000_000;

export type RevenueDisplay = { value: string; unit: "млрд" | "млн" | "сум" };

/** Форматирует Decimal-строку (UZS) в компактный display: «4,12 млрд сум». */
export function formatRevenueShort(decimalStr: string | null): string | null {
  if (decimalStr == null || decimalStr === "") return null;
  const n = Number(decimalStr);
  if (!Number.isFinite(n) || n === 0) return null;
  if (n >= BILLION) {
    const v = (n / BILLION).toFixed(2).replace(".", ",");
    return `${v} млрд сум`;
  }
  if (n >= MILLION) {
    const v = (n / MILLION).toFixed(0);
    return `${v} млн сум`;
  }
  return `${n.toLocaleString("ru-RU")} сум`;
}

/** Decimal-строка → «N млн сум» для tooltip. Округляем до целых млн. */
export function formatRevenueMillions(decimalStr: string): string {
  const n = Number(decimalStr);
  if (!Number.isFinite(n)) return "—";
  const millions = Math.round(n / MILLION);
  return millions.toLocaleString("ru-RU");
}

/** ISO "YYYY-MM" → {monthIndex 1..12, yearShort: "26"}. Возвращает null при mal-format. */
export function parseIsoMonth(iso: string): { monthIndex: number; yearShort: string } | null {
  const m = /^(\d{4})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const year = m[1];
  const month = Number(m[2]);
  if (month < 1 || month > 12) return null;
  return { monthIndex: month, yearShort: year.slice(2) };
}

/** Форматирует YoY как «+18,4%» / «−5,2%» / «—». */
export function formatYoy(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return "—";
  const rounded = Math.round(pct * 10) / 10;
  const sign = rounded > 0 ? "+" : rounded < 0 ? "−" : "";
  const abs = Math.abs(rounded).toFixed(1).replace(".", ",");
  return `${sign}${abs}%`;
}

/** Развёртка business_age_months → {years, months} для i18n. */
export function splitBusinessAge(totalMonths: number): { years: number; months: number } {
  const years = Math.floor(totalMonths / 12);
  const months = totalMonths % 12;
  return { years, months };
}
