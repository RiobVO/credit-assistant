// Zod-схемы 3 шагов формы досье. Маппинг на API — в _form-mapper.ts.
//
// Конвенции форм-значений:
//   • суммы UZS — строки только из цифр (без пробелов / запятых; форматируется на UI)
//   • даты — строки ISO "yyyy-MM-dd" (нативный <input type="date">)
//   • ставка — строка вида "18,5" (запятая или точка); парсится в число при отправке

import { isValid, parse } from "date-fns";
import { z } from "zod";

const INN_RE = /^\d{9}$/;
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const AMOUNT_RE = /^\d+$/;
const RATE_RE = /^\d{1,2}([.,]\d{1,2})?$/;

function parseIso(date: string): Date | null {
  const d = parse(date, "yyyy-MM-dd", new Date());
  return isValid(d) ? d : null;
}

const isoDate = z
  .string()
  .trim()
  .min(1, "Заполните дату")
  .regex(ISO_DATE_RE, "Некорректная дата")
  .refine((v) => parseIso(v) !== null, "Некорректная дата");

const uzsAmount = z
  .string()
  .trim()
  .min(1, "Заполните сумму")
  .regex(AMOUNT_RE, "Только цифры");

const uzsAmountOptional = z
  .string()
  .trim()
  .regex(AMOUNT_RE, "Только цифры")
  .or(z.literal(""));

// CA-027: `annual` — fallback годового total если квартальная разбивка
// недоступна (один FORM_2 Q4 даёт annual без quarters). Если quarters
// заполнены — annual игнорируется при сборке payload (sum quarters важнее).
const quarter = z.object({
  q1: uzsAmountOptional,
  q2: uzsAmountOptional,
  q3: uzsAmountOptional,
  q4: uzsAmountOptional,
  annual: uzsAmountOptional,
});

const yearlyQuarters = z.object({
  y2023: quarter,
  y2024: quarter,
  y2025: quarter,
});

export const legalForms = [
  { code: "llc", label: "ООО / МЧЖ — Общество с ограниченной ответственностью" },
  { code: "jsc", label: "АО — Акционерное общество" },
  { code: "ie", label: "ИП — Индивидуальный предприниматель" },
] as const;

export const loanTerms = [
  { months: 6, label: "6 месяцев" },
  { months: 12, label: "12 месяцев (1 год)" },
  { months: 18, label: "18 месяцев" },
  { months: 24, label: "24 месяца (2 года)" },
  { months: 36, label: "36 месяцев (3 года)" },
  { months: 48, label: "48 месяцев (4 года)" },
  { months: 60, label: "60 месяцев (5 лет)" },
  { months: 84, label: "84 месяца (7 лет)" },
] as const;

export const loanCategories = [
  { code: "working_capital", label: "Оборотный капитал" },
  { code: "investment", label: "Инвестиционный" },
  { code: "fixed_assets", label: "Приобретение основных средств" },
  { code: "refinancing", label: "Рефинансирование" },
  { code: "trade_finance", label: "Торговое финансирование" },
] as const;

// ADR-0024 Session 3: типы обеспечения для secured-variant порога
// LOAN_TO_REVENUE_RATIO. Labels локализуются через i18n keys
// `s3_collateral_<code>` (без hardcoded RU как у loanCategories).
export const collateralTypes = [
  { code: "none", i18nKey: "s3_collateral_none" },
  { code: "real_estate", i18nKey: "s3_collateral_real_estate" },
  { code: "movable", i18nKey: "s3_collateral_movable" },
  { code: "guarantee", i18nKey: "s3_collateral_guarantee" },
  { code: "other", i18nKey: "s3_collateral_other" },
] as const;

export const step1Schema = z
  .object({
    inn: z
      .string()
      .trim()
      .regex(INN_RE, "ИНН должен содержать ровно 9 цифр"),
    name: z.string().trim().min(2, "Заполните наименование"),
    legalForm: z.enum(["llc", "jsc", "ie"]),
    registrationDate: isoDate,
    okedMain: z.string().trim().min(2, "Укажите ОКЭД"),
    directorName: z.string().trim().min(2, "Укажите Ф.И.О. директора"),
    directorAppointedAt: isoDate,
    // CA-038: адрес «Ташкент» проходил min(3); банк требует улицу+дом.
    // Эвристика: ≥15 символов и хотя бы одна цифра (= номер дома/корпуса).
    registeredAddress: z
      .string()
      .trim()
      .min(15, "Адрес должен содержать не менее 15 символов (улица, дом)")
      .refine((v) => /\d/.test(v), "Адрес должен содержать номер дома"),
    // ADR-0024 Session 3: narrow scope для OKVED_CHANGED_12M. Toggle
    // reachable только когда `okedMainChangedAt` пришло с backend (через
    // «Пересобрать с дополнениями»); в brand-new dossier flow поле hidden,
    // default false. Date picker не добавляется — поле parser-driven,
    // editable date = data-integrity bug с future parser re-runs.
    okedChangedByOwner: z.boolean(),
    // Read-only «сигнальное» поле: ISO date если backend знает дату смены
    // ОКЭД (через парсер/ORM), null иначе. UI читает значение для
    // conditional rendering toggle; в submit payload не уходит — backend
    // имеет авторитетное значение через borrower-record.
    okedMainChangedAt: z.string().nullable(),
  })
  .refine(
    ({ registrationDate, directorAppointedAt }) => {
      const reg = parseIso(registrationDate);
      const apt = parseIso(directorAppointedAt);
      if (!reg || !apt) return true;
      return apt.getTime() >= reg.getTime();
    },
    {
      message: "Дата назначения не может быть раньше даты регистрации",
      path: ["directorAppointedAt"],
    },
  );

// VAT-период из загрузки Soliq xltx. Заполняется через POST /api/upload/soliq-xltx,
// сериализуется в payload.vat_periods[0] при финальном submit.
const vatPeriodFromSoliq = z.object({
  year: z.number().int().min(2020).max(2099),
  month: z.number().int().min(1).max(12),
  vatDeclared: z.string().regex(/^\d+(\.\d+)?$/, "Некорректная сумма НДС"),
  esfSellerVat: z.string().regex(/^\d+(\.\d+)?$/, "Некорректная сумма ЭСФ-НДС"),
  organizationName: z.string().optional(),
  submittedAt: z.string().optional(), // ISO date YYYY-MM-DD
  diffPct: z.string().optional(),
  parseWarnings: z.array(z.string()),
  skippedRowsCount: z.number().int().nonnegative(),
});

export type VatPeriodFromSoliq = z.infer<typeof vatPeriodFromSoliq>;

export const step2Schema = z.object({
  revenue: yearlyQuarters,
  netProfit: yearlyQuarters,
  vatDeclared: uzsAmount,
  taxesPaid23: uzsAmountOptional,
  taxesPaid24: uzsAmountOptional,
  taxesPaid25: uzsAmount,
  totalAssets: uzsAmount,
  totalLiabilities: uzsAmount,
  vatPeriod: vatPeriodFromSoliq.nullable(),
  // CA-037: компоненты EBIT/ROE/Debt-to-EBIT — все опциональные hidden поля,
  // заполняются автозаполнением из FORM_2 (income statement) и FORM_1 (balance
  // sheet); UI inputs пока не показываются (TODO: вынести в Step 2 раздел
  // «Углублённые показатели» отдельным тикетом). Применяются только для
  // отчёта последнего года (2025 = current), плюс PBT/interest за 2024 для
  // EBIT YoY.
  profitBeforeTax24: uzsAmountOptional,
  profitBeforeTax25: uzsAmountOptional,
  interestExpense24: uzsAmountOptional,
  interestExpense25: uzsAmountOptional,
  equityEnd25: uzsAmountOptional,
  equityStart25: uzsAmountOptional,
  totalDebtEnd25: uzsAmountOptional,
  totalDebtStart25: uzsAmountOptional,
  assetsStart25: uzsAmountOptional,
  liabilitiesStart25: uzsAmountOptional,
  // ADR-0024 Session 2: запасы для Quick Ratio = (CA − inventory) / CL.
  inventoryEnd25: uzsAmountOptional,
  // ADR-0024 Session 4: FX-компонент для fx_exposure_ratio (доля валютных
  // обязательств в общих обязательствах). Banker вводит вручную в Шаг 2.
  liabilitiesFxEnd25: uzsAmountOptional,
});

export const step3Schema = z.object({
  loanAmount: uzsAmount,
  loanTermMonths: z
    .number()
    .int()
    .positive("Срок должен быть положительным"),
  loanRatePct: z
    .string()
    .trim()
    .regex(RATE_RE, "Формат ставки: 18,5"),
  loanPurpose: z
    .string()
    .trim()
    .min(20, "Опишите цель кредита подробнее (мин. 20 символов)")
    .max(2000, "Максимум 2000 символов"),
  loanCategory: z.enum([
    "working_capital",
    "investment",
    "fixed_assets",
    "refinancing",
    "trade_finance",
  ]),
  // ADR-0024 Session 3: collateral_type для secured-variant
  // LOAN_TO_REVENUE_RATIO. 'none' = unsecured (порог 0.40), остальные
  // = secured (порог 0.70).
  collateralType: z.enum([
    "none",
    "real_estate",
    "movable",
    "guarantee",
    "other",
  ]),
});

export const formSchema = z.object({
  step1: step1Schema,
  step2: step2Schema,
  step3: step3Schema,
});

export type Step1Values = z.infer<typeof step1Schema>;
export type Step2Values = z.infer<typeof step2Schema>;
export type Step3Values = z.infer<typeof step3Schema>;
export type FormValues = z.infer<typeof formSchema>;

export const stepFieldPaths: Record<1 | 2 | 3, string[]> = {
  1: ["step1"],
  2: ["step2"],
  3: ["step3"],
};

export function defaultFormValues(): FormValues {
  return {
    step1: {
      inn: "",
      name: "",
      legalForm: "llc",
      registrationDate: "",
      okedMain: "",
      directorName: "",
      directorAppointedAt: "",
      registeredAddress: "",
      // ADR-0024 Session 3: default false для brand-new dossiers. Prefill из
      // existing borrower (через CA-058 sessionStorage) перетирает значение
      // на actual flag из БД.
      okedChangedByOwner: false,
      okedMainChangedAt: null,
    },
    step2: {
      revenue: {
        y2023: { q1: "", q2: "", q3: "", q4: "", annual: "" },
        y2024: { q1: "", q2: "", q3: "", q4: "", annual: "" },
        y2025: { q1: "", q2: "", q3: "", q4: "", annual: "" },
      },
      netProfit: {
        y2023: { q1: "", q2: "", q3: "", q4: "", annual: "" },
        y2024: { q1: "", q2: "", q3: "", q4: "", annual: "" },
        y2025: { q1: "", q2: "", q3: "", q4: "", annual: "" },
      },
      vatDeclared: "",
      taxesPaid23: "",
      taxesPaid24: "",
      taxesPaid25: "",
      totalAssets: "",
      totalLiabilities: "",
      vatPeriod: null,
      // CA-037: hidden поля для EBIT/ROE/Debt-to-EBIT (см. step2Schema).
      profitBeforeTax24: "",
      profitBeforeTax25: "",
      interestExpense24: "",
      interestExpense25: "",
      equityEnd25: "",
      equityStart25: "",
      totalDebtEnd25: "",
      totalDebtStart25: "",
      assetsStart25: "",
      liabilitiesStart25: "",
      inventoryEnd25: "",
      liabilitiesFxEnd25: "",
    },
    step3: {
      loanAmount: "",
      loanTermMonths: 24,
      loanRatePct: "",
      loanPurpose: "",
      loanCategory: "working_capital",
      // ADR-0024 Session 3: default 'none' (unsecured, conservative). Analyst
      // явно выбирает secured-вариант через UI Step 3.
      collateralType: "none",
    },
  };
}

export const REPORT_YEARS = [2023, 2024, 2025] as const;
export type ReportYear = (typeof REPORT_YEARS)[number];

export function parseDateIso(s: string): Date | null {
  return parseIso(s);
}
