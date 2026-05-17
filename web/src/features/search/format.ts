// Phase 2 (DS-PHASE-2): хелперы форматирования для result-card.
// Цифры выручки → «4,12 млрд сум» / «560 млн сум»; ISO month → «Май 26»;
// business_age_months → {years, months} для i18n plural-template.
// T0.4 B4: locale-aware суффиксы — RU числа + UZ-суффикс (mlrd / mln / soʻm)
// для bank UZ-mode, консистентно с dossier formatBigUzs.

const MILLION = 1_000_000;
const BILLION = 1_000_000_000;

export type UzsLocale = "ru" | "uz";

const SUFFIX = {
  ru: { billion: "млрд сум", million: "млн сум", currency: "сум" },
  // U+02BB MODIFIER LETTER TURNED COMMA в "soʻm" — стандартный апостроф
  // латинского узбекского; см. config/pdf-i18n/uz.json.
  uz: { billion: "mlrd soʻm", million: "mln soʻm", currency: "soʻm" },
} as const;

/** Форматирует Decimal-строку (UZS) в компактный display: «4,12 млрд сум». */
export function formatRevenueShort(
  decimalStr: string | null,
  locale: UzsLocale,
): string | null {
  if (decimalStr == null || decimalStr === "") return null;
  const n = Number(decimalStr);
  if (!Number.isFinite(n) || n === 0) return null;
  const s = SUFFIX[locale];
  if (n >= BILLION) {
    const v = (n / BILLION).toFixed(2).replace(".", ",");
    return `${v} ${s.billion}`;
  }
  if (n >= MILLION) {
    const v = (n / MILLION).toFixed(0);
    return `${v} ${s.million}`;
  }
  return `${n.toLocaleString("ru-RU")} ${s.currency}`;
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
