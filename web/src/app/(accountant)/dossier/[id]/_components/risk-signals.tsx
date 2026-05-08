import { ChevronRight } from "lucide-react";

import type { RedFlagDto, Severity } from "@/lib/api";
import { cn } from "@/lib/utils";

const SEVERITY_DOT: Record<Severity, string> = {
  low: "bg-[var(--ca-success)]",
  medium: "bg-[var(--ca-warning)]",
  high: "bg-[var(--ca-danger)]",
  critical: "bg-[var(--ca-danger)]",
};

const SEVERITY_PILL: Record<Severity, string> = {
  low: "border-[#BFE2D2] bg-[var(--ca-success-50)] text-[var(--ca-success)]",
  medium: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--ca-warning)]",
  high: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--ca-danger)]",
  critical: "border-[var(--ca-danger)] bg-[#FCE7E5] text-[var(--ca-danger)]",
};

const RULE_LABEL: Record<string, string> = {
  LOAN_TO_REVENUE_RATIO: "Долг / EBITDA",
  TAX_PAYMENT_DELAYS: "Уплата налогов",
  SINGLE_BUYER_CONCENTRATION: "Концентрация выручки",
  RECEIVABLES_CONCENTRATION: "Концентрация дебиторов",
  REVENUE_DROP_MOM_30: "Падение выручки MoM",
  REVENUE_DROP_YOY_50: "Падение выручки YoY",
  NEGATIVE_PROFIT_3Q: "Отриц. прибыль 3 кв.",
  VAT_GROWTH_NO_REVENUE: "НДС без роста выручки",
  VAT_ESF_MISMATCH: "Расхождение НДС / ЭСФ",
  LOW_MARGIN_HIGH_TURNOVER: "Низкая маржа",
  SINGLE_SUPPLIER_CONCENTRATION: "Концентрация поставщиков",
  NEW_COUNTERPARTY_LARGE_SHARE: "Новые контрагенты",
  SHELL_COMPANY_PARTNERS: "Контрагенты-однодневки",
  CIRCULAR_INVOICING: "Циклические ЭСФ",
  BANK_ACCOUNT_FROZEN_12M: "Блокировки счёта",
  TAX_PENALTIES_CURRENT_YEAR: "Пеня по налогам",
  DIRECTOR_CHANGED_6M: "Смена директора",
  OKVED_CHANGED_12M: "Смена ОКВЭД",
};

export function RiskSignals({ flags }: { flags: RedFlagDto[] }) {
  return (
    <section className="flex h-full flex-col rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
            Сигналы риска
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
            {flags.length} {pluralFlags(flags.length)} из 17 проверенных
          </p>
        </div>
      </header>

      {flags.length === 0 ? (
        <div className="flex-1 px-[22px] py-10 text-center text-[13px] text-[var(--ca-ink-500)]">
          Все проверки пройдены.
        </div>
      ) : (
        <ul className="divide-y divide-[var(--ca-border)]">
          {flags.map((f) => (
            <SignalRow key={`${f.rule_id}-${f.detected_at}`} flag={f} />
          ))}
        </ul>
      )}
    </section>
  );
}

function SignalRow({ flag }: { flag: RedFlagDto }) {
  const label = RULE_LABEL[flag.rule_id] ?? flag.rule_id;
  const value = renderEvidenceValue(flag);

  return (
    <li className="flex items-center gap-3 px-[22px] py-3">
      <span className={cn("size-2 flex-none rounded-full", SEVERITY_DOT[flag.severity])} />
      <div className="min-w-0 flex-1">
        <div className="text-[13.5px] font-medium text-[var(--ca-ink-900)]">
          {label}
        </div>
        <div className="mt-0.5 truncate text-[11.5px] text-[var(--ca-ink-500)]">
          {flag.message}
        </div>
      </div>
      {value ? (
        <span
          className={cn(
            "inline-flex items-center rounded-full border px-2.5 py-px font-mono text-[12px] font-semibold whitespace-nowrap",
            SEVERITY_PILL[flag.severity],
          )}
        >
          {value}
        </span>
      ) : null}
      <ChevronRight className="size-4 flex-none text-[var(--ca-ink-400)]" />
    </li>
  );
}

// Достаём «главное число» из evidence по rule_id, чтобы показать его в pill.
function renderEvidenceValue(flag: RedFlagDto): string | null {
  const e = flag.evidence;
  switch (flag.rule_id) {
    case "LOAN_TO_REVENUE_RATIO":
      return e.ratio ? `${e.ratio}x` : null;
    case "TAX_PAYMENT_DELAYS":
      return e.yoy_pct ? `${e.yoy_pct}%` : null;
    case "SINGLE_BUYER_CONCENTRATION":
    case "SINGLE_SUPPLIER_CONCENTRATION":
    case "RECEIVABLES_CONCENTRATION":
    case "NEW_COUNTERPARTY_LARGE_SHARE":
      if (typeof e.top1_share === "string") {
        const pct = (parseFloat(e.top1_share) * 100).toFixed(0);
        return `${pct}%`;
      }
      return null;
    default:
      return null;
  }
}

function pluralFlags(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "сигналов";
  if (mod10 === 1) return "сигнал";
  if (mod10 >= 2 && mod10 <= 4) return "сигнала";
  return "сигналов";
}
