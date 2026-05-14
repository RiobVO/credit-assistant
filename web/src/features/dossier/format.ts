// Хелперы форматирования для KPI-карточек и осей графиков.
// UZS — большие числа, поэтому показываем «млрд / млн» с одним знаком после запятой.
// Banking UZ convention (T0.4 B4): RU-numbers (`ru-RU` toLocaleString) везде,
// меняем только суффикс на UZ для locale === "uz" — UZ-аналитик привык к
// RU-числовому формату, а PDF единым стилем (см. config/pdf-i18n/uz.json).

export type UzsLocale = "ru" | "uz";

const NBSP = " ";

const SUFFIX = {
  ru: { billion: "млрд", million: "млн", thousand: "тыс", currency: "сум" },
  // U+02BB MODIFIER LETTER TURNED COMMA — стандартный апостроф латинского
  // узбекского (oʻ, gʻ, ʼ), консистентно с config/pdf-i18n/uz.json («soʻm»).
  uz: { billion: "mlrd", million: "mln", thousand: "ming", currency: "soʻm" },
} as const;

export function formatBigUzs(amount: number, locale: UzsLocale): string {
  if (!Number.isFinite(amount)) return "—";
  const s = SUFFIX[locale];
  const abs = Math.abs(amount);
  if (abs >= 1_000_000_000) {
    return `${formatRu(amount / 1_000_000_000, 1)}${NBSP}${s.billion}${NBSP}${s.currency}`;
  }
  if (abs >= 1_000_000) {
    return `${formatRu(amount / 1_000_000, 1)}${NBSP}${s.million}${NBSP}${s.currency}`;
  }
  if (abs >= 1_000) {
    return `${formatRu(amount / 1_000, 1)}${NBSP}${s.thousand}${NBSP}${s.currency}`;
  }
  return `${formatRu(amount, 0)}${NBSP}${s.currency}`;
}

export function formatPct(value: number, fractionDigits: number = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${formatRu(value, fractionDigits)}%`;
}

export function formatRatio(value: number): string {
  if (!Number.isFinite(value)) return "—";
  // Большие коэффициенты (DSCR, Debt/Equity, прочие x-метрики) ломают
  // ширину pill/карточки; малые — теряют смысл при округлении до 0,1.
  if (value > 999) return ">999x";
  if (value > 0 && value < 0.01) return "<0,01x";
  return `${formatRu(value, 1)}x`;
}

export function formatYoy(pct: number): string {
  if (!Number.isFinite(pct)) return "—";
  // Экстремальные значения (например, рост с 0 → деление на ε) ломают вёрстку
  // KPI-карточки. Точное число там не имеет смысла, важен сам факт «зашкаливает».
  if (pct > 999) return ">+999%";
  if (pct < -999) return "<−999%";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${formatRu(pct, 1)}%`;
}

export function formatMonthShort(yyyyMm: string): string {
  const [yyyy, mm] = yyyyMm.split("-");
  return `${mm}/${yyyy.slice(2)}`;
}

function formatRu(value: number, fractionDigits: number): string {
  return value.toLocaleString("ru-RU", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}
