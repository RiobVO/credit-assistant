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

import type { FormValues } from "./schema";
import { yearTotal } from "./lib/finance";

type Money = { amount: string; currency: "UZS" };

type DateRange = { start: string; end: string };

type FinancialReport = {
  period: DateRange;
  revenue: Money;
  net_profit: Money;
  // CA-044: optional. Пустое поле формы → undefined в payload → null в БД.
  // Money(0) сохраняем только когда юзер осознанно ввёл "0".
  taxes_paid?: Money;
  vat_declared?: Money;
  assets?: Money;
  liabilities?: Money;
  // CA-037: income-statement расширения (EBIT прокси компоненты).
  profit_before_tax?: Money;
  interest_expense?: Money;
  // CA-037: balance-sheet расширения (ROE + Debt-to-EBIT).
  equity?: Money;
  total_debt?: Money;
  assets_period_start?: Money;
  liabilities_period_start?: Money;
  equity_period_start?: Money;
  total_debt_period_start?: Money;
  // ADR-0024 Session 2: inventory для Quick Ratio.
  inventory?: Money;
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
  // ADR-0024 Session 3: collateral_type для secured-variant порога
  // LOAN_TO_REVENUE_RATIO. 'none' = unsecured (порог 0.40),
  // остальные = secured (порог 0.70).
  collateral_type: "none" | "real_estate" | "movable" | "guarantee" | "other";
};

export type ManualInputPayload = {
  borrower: {
    inn: string;
    name: string;
    legal_form: "llc" | "jsc" | "ie";
    registration_date: string;
    director_name: string;
    director_appointed_at: string;
    oked_main: string;
    registered_address: string;
    // ADR-0024 Session 3: narrow для OKVED_CHANGED_12M. Default false для
    // brand-new dossiers; true только когда analyst поставил toggle во
    // flow «Пересобрать с дополнениями».
    oked_changed_by_owner: boolean;
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

// CA-044: пустая строка → undefined, не Money(0). Это даёт backend
// различать «не заполнено» (null) и «осознанно ноль» (Money(0)).
function moneyOptional(digits: string): Money | undefined {
  return digits ? { amount: digits, currency: "UZS" } : undefined;
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
      };
      // CA-044: taxes_paid опционален. Пустое поле → не отправляем (None в БД),
      // не фабрикуем Money(0) в банковский документ.
      const tax = moneyOptional(taxesByYear[y]);
      if (tax) report.taxes_paid = tax;
      if (isLatest) {
        if (step2.vatDeclared) report.vat_declared = money(step2.vatDeclared);
        if (step2.totalAssets) report.assets = money(step2.totalAssets);
        if (step2.totalLiabilities) report.liabilities = money(step2.totalLiabilities);
        // CA-037: EBIT/ROE/Debt-to-EBIT компоненты — все опциональные, идут
        // только в latest year reporting period (2025). PBT/interest для 2024
        // подключаются отдельной веткой ниже (для EBIT YoY).
        const pbt25 = moneyOptional(step2.profitBeforeTax25);
        if (pbt25) report.profit_before_tax = pbt25;
        const intr25 = moneyOptional(step2.interestExpense25);
        if (intr25) report.interest_expense = intr25;
        const eqEnd = moneyOptional(step2.equityEnd25);
        if (eqEnd) report.equity = eqEnd;
        const eqStart = moneyOptional(step2.equityStart25);
        if (eqStart) report.equity_period_start = eqStart;
        const debtEnd = moneyOptional(step2.totalDebtEnd25);
        if (debtEnd) report.total_debt = debtEnd;
        const debtStart = moneyOptional(step2.totalDebtStart25);
        if (debtStart) report.total_debt_period_start = debtStart;
        const aStart = moneyOptional(step2.assetsStart25);
        if (aStart) report.assets_period_start = aStart;
        const lStart = moneyOptional(step2.liabilitiesStart25);
        if (lStart) report.liabilities_period_start = lStart;
        // ADR-0024 Session 2: inventory как latest-only (UI вводит одно значение).
        const inv = moneyOptional(step2.inventoryEnd25);
        if (inv) report.inventory = inv;
      } else if (y === 2024) {
        // CA-037: PBT/interest_expense за 2024 — только для EBIT YoY%
        // в досье. Полный balance snapshot 2024 не требуется (UI карточки
        // показывают KPI текущего периода).
        const pbt24 = moneyOptional(step2.profitBeforeTax24);
        if (pbt24) report.profit_before_tax = pbt24;
        const intr24 = moneyOptional(step2.interestExpense24);
        if (intr24) report.interest_expense = intr24;
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
      // CA-044: quarterly без taxes_paid — годовой taxes уже в annual_reports.
      // Прежний dummy Money(0) попадал в payload и сериализовался в БД.
      quarterly.push({
        period: QUARTER_RANGES[q](y),
        revenue: money(revDigits || "0"),
        net_profit: money(profitDigits || "0"),
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
      oked_main: step1.okedMain,
      registered_address: step1.registeredAddress,
      oked_changed_by_owner: step1.okedChangedByOwner,
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
      collateral_type: step3.collateralType,
    };
  }

  return payload;
}
