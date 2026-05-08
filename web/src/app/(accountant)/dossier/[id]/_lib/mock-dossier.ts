// Mock-данные для страницы /dossier/[id] на этапе Phase 3.A (UI-only).
// На Phase 3.B заменяется на useQuery → GET /api/dossier/{id}.
// Числа взяты с дизайн-скрина: ООО «Полярная Звезда», score 73,
// выручка 24,5 млрд / EBITDA 418 млн / ROE 8,4% / Debt/EBITDA 3,8x.

import type { DossierViewDto, RedFlagDto } from "@/lib/api";

const RED_FLAGS: RedFlagDto[] = [
  {
    rule_id: "LOAN_TO_REVENUE_RATIO",
    rule_version: "1.0",
    severity: "high",
    source: "Базель III leverage; внутренние методики Hamkorbank",
    message: "Долг к EBITDA 3.8x — выше норматива 3.0x.",
    evidence: { ratio: "3.8", threshold: "3.0" },
    detected_at: "2025-05-09T08:00:00Z",
  },
  {
    rule_id: "TAX_PAYMENT_DELAYS",
    rule_version: "1.0",
    severity: "medium",
    source: "ЦБ РУз положение №27-п, п.4.5",
    message: "Снижение уплаты налогов на 14,2% YoY.",
    evidence: { yoy_pct: "-14.2" },
    detected_at: "2025-05-09T08:00:00Z",
  },
  {
    rule_id: "SINGLE_BUYER_CONCENTRATION",
    rule_version: "1.0",
    severity: "medium",
    source: "Базель III concentration risk",
    message: "Концентрация выручки на топ-1 покупателе.",
    evidence: { top1_share: "0.58" },
    detected_at: "2025-05-09T08:00:00Z",
  },
  {
    rule_id: "RECEIVABLES_CONCENTRATION",
    rule_version: "1.0",
    severity: "medium",
    source: "Внутренние методики Kapitalbank",
    message: "Концентрация дебиторов: 38% на топ-1 контрагенте.",
    evidence: { top1_share: "0.38" },
    detected_at: "2025-05-09T08:00:00Z",
  },
];

function buildSparkline(start: number, end: number, points: number = 12): number[] {
  const step = (end - start) / (points - 1);
  return Array.from({ length: points }, (_, i) => Math.round(start + step * i));
}

function buildMonthlyRevenue(): DossierViewDto["monthly_revenue_24m"] {
  // 24 месяца, конец = май 2025. Сезонные пики в декабре каждого года.
  const months: DossierViewDto["monthly_revenue_24m"] = [];
  const base = 1_900_000_000;
  let trendAcc = base;
  for (let i = 23; i >= 0; i--) {
    const date = new Date(2025, 4 - i, 1); // май 2025 минус i месяцев
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    const month = `${yyyy}-${mm}`;
    const isDecember = date.getMonth() === 11;
    const seasonalPeak = isDecember ? 1.45 : 1;
    const wave = 1 + 0.18 * Math.sin((i / 24) * Math.PI * 2);
    const revenue = Math.round(base * wave * seasonalPeak);
    trendAcc = Math.round(trendAcc * 0.85 + revenue * 0.15);
    months.push({ month, revenue, trend: trendAcc, is_peak: isDecember });
  }
  return months;
}

export function mockDossier(id: string): DossierViewDto {
  return {
    dossier_id: id,
    borrower_inn_masked: "XXXXXX5821",
    as_of: "2025-05-09",
    red_flags: RED_FLAGS,
    risk_score: {
      score: 73,
      recommendation: "review",
      severity_breakdown: { high: 1, medium: 3 },
    },
    rules_evaluated: 17,
    borrower: {
      inn: "307895821",
      name: "ООО «Полярная Звезда»",
      legal_form: "llc",
      registration_date: "2018-03-14",
      director_name: "Иванова А.С.",
      director_appointed_at: "2022-07-01",
      okved_main: "46.39 — Опт. торговля прод. товарами",
      registered_address: "Ташкент, Юнусабадский р-н, ул. Алмазар 16",
    },
    application: {
      id: "BR-2025-0418",
      status: "in_review",
    },
    kpis: {
      revenue_ltm: {
        value: 24_500_000_000,
        unit: "UZS",
        yoy_pct: -8.2,
        sparkline: buildSparkline(26_800_000_000, 24_500_000_000),
      },
      ebitda: {
        value: 418_000_000,
        unit: "UZS",
        yoy_pct: 6.4,
        sparkline: buildSparkline(390_000_000, 418_000_000),
      },
      roe: {
        value: 8.4,
        unit: "PCT",
        yoy_pct: 1.1,
        sparkline: buildSparkline(7.3, 8.4),
      },
      debt_to_ebitda: {
        value: 3.8,
        unit: "RATIO",
        yoy_pct: 12.5,
        sparkline: buildSparkline(3.4, 3.8),
      },
    },
    monthly_revenue_24m: buildMonthlyRevenue(),
  };
}
