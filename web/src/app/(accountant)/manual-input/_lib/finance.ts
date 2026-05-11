// Чистые финансовые хелперы для Step 2/3. Никаких побочных эффектов.

const RU_NUMBER = new Intl.NumberFormat("ru-RU", {
  useGrouping: true,
  maximumFractionDigits: 0,
});

const RU_NUMBER_RATE = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 2,
});

export function digitsOnly(value: string): string {
  return value.replace(/\D+/g, "");
}

export function formatUzs(amountDigits: string): string {
  if (!amountDigits) return "";
  const n = Number.parseInt(amountDigits, 10);
  if (Number.isNaN(n)) return "";
  return RU_NUMBER.format(n);
}

export function formatUzsRich(amountDigits: string): string {
  const formatted = formatUzs(amountDigits);
  return formatted ? `${formatted} UZS` : "";
}

export function parseAmount(input: string): number {
  const cleaned = digitsOnly(input);
  if (!cleaned) return 0;
  return Number.parseInt(cleaned, 10);
}

export function parseRate(input: string): number {
  // "18,5" / "18.5" / "18" → 18.5 / 18.5 / 18
  if (!input) return 0;
  const normalised = input.replace(/\s+/g, "").replace(",", ".");
  const v = Number.parseFloat(normalised);
  return Number.isFinite(v) ? v : 0;
}

export function formatRate(value: number): string {
  return RU_NUMBER_RATE.format(value).replace(".", ",");
}

export function sumQuarters(q: {
  q1: string;
  q2: string;
  q3: string;
  q4: string;
  annual?: string;
}): number {
  return (
    parseAmount(q.q1) + parseAmount(q.q2) + parseAmount(q.q3) + parseAmount(q.q4)
  );
}

// CA-033: различить «не введено» (все cells пустые) от «введён ноль».
// parseAmount("") === 0 теряет это различие; для pre-score UI нам нужно
// показывать neutral state когда данных нет, а red — когда введён явный 0.
export function hasAnyQuarterValue(q: {
  q1: string;
  q2: string;
  q3: string;
  q4: string;
  annual?: string;
}): boolean {
  return [q.q1, q.q2, q.q3, q.q4, q.annual ?? ""].some(
    (s) => digitsOnly(s).length > 0,
  );
}

// CA-027: годовое total — sum квартальных, либо annual если квартальные пустые
// (FORM_2 Q4 даёт annual без квартальной разбивки). Если оба заполнены —
// побеждают quarters (явный пользовательский ввод важнее автозаполненного).
export function yearTotal(q: {
  q1: string;
  q2: string;
  q3: string;
  q4: string;
  annual?: string;
}): number {
  const quarterSum = sumQuarters(q);
  if (quarterSum > 0) return quarterSum;
  return q.annual ? parseAmount(q.annual) : 0;
}

export function computeAnnuityMonthly(
  principal: number,
  annualRatePct: number,
  termMonths: number,
): number {
  if (principal <= 0 || termMonths <= 0) return 0;
  const r = annualRatePct / 100 / 12;
  if (r === 0) return Math.round(principal / termMonths);
  const factor = (r * Math.pow(1 + r, termMonths)) / (Math.pow(1 + r, termMonths) - 1);
  return Math.round(principal * factor);
}

export function computeOverpayment(
  monthlyPayment: number,
  termMonths: number,
  principal: number,
): number {
  return Math.max(0, monthlyPayment * termMonths - principal);
}

// DSCR = годовая чистая прибыль (прокси: net_profit_2025) / годовые платежи.
// Эвристика для pre-score: предположим, что вся годовая чистая прибыль
// доступна для обслуживания долга.
//
// CA-033: null-семантика — null означает «недостаточно данных», явные 0
// и отрицательные значения возвращаются как числа (это валидные red-flag
// сигналы, не «нет данных»):
// - monthlyPayment null/<=0 → null (нет параметров кредита)
// - annualNetProfit null → null (нет фин.отчёта)
// - annualNetProfit < 0 → отрицательный DSCR (убыток, classify → red)
// - annualNetProfit === 0 → 0 (нулевая прибыль, classify → red)
export function computeDscr(
  annualNetProfit: number | null,
  monthlyPayment: number | null,
): number | null {
  if (monthlyPayment == null || monthlyPayment <= 0) return null;
  if (annualNetProfit == null) return null;
  return annualNetProfit / (monthlyPayment * 12);
}

export function classifyDscrRisk(dscr: number | null): {
  label: "Низкий риск" | "Средний риск" | "Высокий риск" | "Недостаточно данных";
  tone: "success" | "warning" | "danger" | "neutral";
} {
  if (dscr == null) return { label: "Недостаточно данных", tone: "neutral" };
  if (dscr >= 1.5) return { label: "Низкий риск", tone: "success" };
  if (dscr >= 1.25) return { label: "Средний риск", tone: "warning" };
  return { label: "Высокий риск", tone: "danger" };
}

export function computeDebtToAssets(
  totalLiabilities: number,
  totalAssets: number,
): number {
  if (totalAssets <= 0) return 0;
  return totalLiabilities / totalAssets;
}

export function computeEquity(
  totalAssets: number,
  totalLiabilities: number,
): number {
  return totalAssets - totalLiabilities;
}

// CA-034: null-семантика — null = «недостаточно данных». Явные числа
// (включая 0 и отрицательные) — валидные сигналы.
export function computeMarginPct(
  netProfit: number,
  revenue: number,
): number | null {
  if (revenue <= 0) return null;
  return (netProfit / revenue) * 100;
}

// CA-034: null когда базовый год пустой (start <= 0) или years <= 0.
// Деление на ноль / Infinity не должно рендериться как «0.0%» — это
// семантически «нет данных», а не нулевой рост.
export function computeCagrPct(
  startValue: number,
  endValue: number,
  years: number,
): number | null {
  if (startValue <= 0 || years <= 0) return null;
  return (Math.pow(endValue / startValue, 1 / years) - 1) * 100;
}

// CA-033: null если выручка отсутствует ИЛИ === 0 (деление на ноль =
// «нет данных» по смыслу: нулевая выручка не позволяет посчитать долговую
// нагрузку).
export function computeDebtToRevenuePct(
  loanAmount: number,
  annualRevenue: number | null,
): number | null {
  if (annualRevenue == null || annualRevenue === 0) return null;
  return (loanAmount / annualRevenue) * 100;
}
