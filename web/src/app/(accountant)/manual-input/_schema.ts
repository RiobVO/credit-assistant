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

export const step1Schema = z
  .object({
    inn: z
      .string()
      .trim()
      .regex(INN_RE, "ИНН должен содержать ровно 9 цифр"),
    name: z.string().trim().min(2, "Заполните наименование"),
    legalForm: z.enum(["llc", "jsc", "ie"]),
    registrationDate: isoDate,
    okvedMain: z.string().trim().min(2, "Укажите ОКВЭД"),
    directorName: z.string().trim().min(2, "Укажите Ф.И.О. директора"),
    directorAppointedAt: isoDate,
    registeredAddress: z.string().trim().min(3, "Укажите юридический адрес"),
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
      okvedMain: "",
      directorName: "",
      directorAppointedAt: "",
      registeredAddress: "",
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
    },
    step3: {
      loanAmount: "",
      loanTermMonths: 24,
      loanRatePct: "",
      loanPurpose: "",
      loanCategory: "working_capital",
    },
  };
}

export const REPORT_YEARS = [2023, 2024, 2025] as const;
export type ReportYear = (typeof REPORT_YEARS)[number];

export function parseDateIso(s: string): Date | null {
  return parseIso(s);
}
