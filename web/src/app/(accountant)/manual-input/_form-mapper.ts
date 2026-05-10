// Маппинг FormValues → payload для POST /api/manual-input.
// Pydantic-схема: src/interfaces/api/shared/dossier_schema.py.
//
// Договорённости (PROJECT_BRIEF Section 5, ADR 0004):
//   • Step 2 квартальные данные суммируются в annual_reports — для 2025 включаем
//     полный набор (taxes/vat/assets/liabilities). Для 2023/2024 включаем
//     revenue/net_profit + per-year taxes_paid (CA-004), VAT/assets/liabilities
//     остаются только на 2025.
//   • Помимо annual_reports эмитим quarterly_reports для квартала с любыми
//     данными — чтобы NEGATIVE_PROFIT_3Q работал.
//   • Step 3 → `loan_request` объект (CA-005): amount/term_months/rate_pct/
//     purpose/category. Ставка из формы "18,5" → "18.5" (Decimal-friendly).

import { format } from "date-fns";

import type { FormValues } from "./_schema";
import { yearTotal } from "./_lib/finance";

type Money = { amount: string; currency: "UZS" };

type DateRange = { start: string; end: string };

type FinancialReport = {
  period: DateRange;
  revenue: Money;
  net_profit: Money;
  taxes_paid: Money;
  vat_declared?: Money;
  assets?: Money;
  liabilities?: Money;
};

type VatPeriodReport = {
  period: DateRange;
  vat_declared?: Money;
  esf_seller_vat_total?: Money;
  submitted_at?: string;
};

type LoanRequest = {
  amount: Money;
  term_months: number;
  rate_pct: string; // Decimal как строка
  purpose: string;
  category: string;
};

export type ManualInputPayload = {
  borrower: {
    inn: string;
    name: string;
    legal_form: "llc" | "jsc" | "ie";
    registration_date: string;
    director_name: string;
    director_appointed_at: string;
    okved_main: string;
    registered_address: string;
  };
  as_of: string;
  annual_reports: FinancialReport[];
  quarterly_reports: FinancialReport[];
  vat_periods?: VatPeriodReport[];
  loan_request?: LoanRequest;
};

const QUARTER_RANGES = {
  q1: (year: number) => ({ start: `${year}-01-01`, end: `${year}-03-31` }),
  q2: (year: number) => ({ start: `${year}-04-01`, end: `${year}-06-30` }),
  q3: (year: number) => ({ start: `${year}-07-01`, end: `${year}-09-30` }),
  q4: (year: number) => ({ start: `${year}-10-01`, end: `${year}-12-31` }),
} as const;

function money(digits: string): Money {
  return { amount: digits || "0", currency: "UZS" };
}

export function formValuesToPayload(values: FormValues): ManualInputPayload {
  const { step1, step2, step3 } = values;
  const today = format(new Date(), "yyyy-MM-dd");

  const years = [2023, 2024, 2025] as const;

  const taxesByYear: Record<(typeof years)[number], string> = {
    2023: step2.taxesPaid23,
    2024: step2.taxesPaid24,
    2025: step2.taxesPaid25,
  };

  const annual: FinancialReport[] = years
    .map((y) => {
      const yKey = `y${y}` as const;
      // CA-027: yearTotal даёт annual fallback если квартальные пустые
      // (FORM_2 Q4 заполняет только annual).
      const revenueTotal = yearTotal(step2.revenue[yKey]);
      const profitTotal = yearTotal(step2.netProfit[yKey]);
      const isLatest = y === 2025;
      const hasData = revenueTotal > 0 || profitTotal > 0 || isLatest;
      if (!hasData) return null;
      const report: FinancialReport = {
        period: { start: `${y}-01-01`, end: `${y}-12-31` },
        revenue: money(String(revenueTotal)),
        net_profit: money(String(profitTotal)),
        taxes_paid: money(taxesByYear[y]),
      };
      if (isLatest) {
        if (step2.vatDeclared) report.vat_declared = money(step2.vatDeclared);
        if (step2.totalAssets) report.assets = money(step2.totalAssets);
        if (step2.totalLiabilities) report.liabilities = money(step2.totalLiabilities);
      }
      return report;
    })
    .filter((x): x is FinancialReport => x !== null);

  const quarterly: FinancialReport[] = [];
  for (const y of years) {
    const yKey = `y${y}` as const;
    for (const q of ["q1", "q2", "q3", "q4"] as const) {
      const revDigits = step2.revenue[yKey][q];
      const profitDigits = step2.netProfit[yKey][q];
      if (!revDigits && !profitDigits) continue;
      quarterly.push({
        period: QUARTER_RANGES[q](y),
        revenue: money(revDigits || "0"),
        net_profit: money(profitDigits || "0"),
        taxes_paid: money("0"),
      });
    }
  }

  const payload: ManualInputPayload = {
    borrower: {
      inn: step1.inn,
      name: step1.name,
      legal_form: step1.legalForm,
      registration_date: step1.registrationDate,
      director_name: step1.directorName,
      director_appointed_at: step1.directorAppointedAt,
      okved_main: step1.okvedMain,
      registered_address: step1.registeredAddress,
    },
    as_of: today,
    annual_reports: annual,
    quarterly_reports: quarterly,
  };

  if (step2.vatPeriod) {
    const { year, month, vatDeclared, esfSellerVat, submittedAt } = step2.vatPeriod;
    const lastDay = new Date(year, month, 0).getDate();
    const mm = String(month).padStart(2, "0");
    const dd = String(lastDay).padStart(2, "0");
    payload.vat_periods = [
      {
        period: { start: `${year}-${mm}-01`, end: `${year}-${mm}-${dd}` },
        vat_declared: { amount: vatDeclared, currency: "UZS" },
        esf_seller_vat_total: { amount: esfSellerVat, currency: "UZS" },
        ...(submittedAt ? { submitted_at: submittedAt } : {}),
      },
    ];
  }

  if (step3.loanAmount) {
    payload.loan_request = {
      amount: money(step3.loanAmount),
      term_months: step3.loanTermMonths,
      rate_pct: step3.loanRatePct.replace(",", "."),
      purpose: step3.loanPurpose,
      category: step3.loanCategory,
    };
  }

  return payload;
}
