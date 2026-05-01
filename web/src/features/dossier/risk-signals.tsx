"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import type { RedFlagDto, Severity } from "@/lib/api";
import { cn } from "@/lib/utils";

const SEVERITY_DOT: Record<Severity, string> = {
  low: "bg-[var(--state-ok-fg)]",
  medium: "bg-[var(--state-warn-fg)]",
  high: "bg-[var(--state-bad-fg)]",
  critical: "bg-[var(--state-bad-fg)]",
};

const SEVERITY_PILL: Record<Severity, string> = {
  low: "border-[#BFE2D2] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
  medium: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--state-warn-fg)]",
  high: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--state-bad-fg)]",
  critical: "border-[var(--state-bad-fg)] bg-[#FCE7E5] text-[var(--state-bad-fg)]",
};

const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
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
  NEGATIVE_EQUITY: "Отрицательный капитал",
};

// CA-050: accordion-rows + actual rules_evaluated count из API
// (вместо хардкода 17 — реестр после CA-049 содержит 19 правил).
export function RiskSignals({
  flags,
  rulesEvaluated,
}: {
  flags: RedFlagDto[];
  rulesEvaluated: number;
}) {
  return (
    <section className="flex h-full flex-col rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ink-1)]">
            Сигналы риска
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {flags.length} {pluralFlags(flags.length)} из {rulesEvaluated} проверенных
          </p>
        </div>
      </header>

      {flags.length === 0 ? (
        <div className="flex-1 px-[22px] py-10 text-center text-[13px] text-[var(--ink-3)]">
          Все проверки пройдены.
        </div>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {flags.map((f) => (
            <SignalRow key={`${f.rule_id}-${f.detected_at}`} flag={f} />
          ))}
        </ul>
      )}
    </section>
  );
}

function SignalRow({ flag }: { flag: RedFlagDto }) {
  const [expanded, setExpanded] = useState(false);
  const label = RULE_LABEL[flag.rule_id] ?? flag.rule_id;
  const value = renderEvidenceValue(flag);
  const Chevron = expanded ? ChevronDown : ChevronRight;
  const evidenceEntries = Object.entries(flag.evidence ?? {});

  return (
    <li className="px-[22px]">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-3 py-3 text-left transition-colors hover:bg-[#FAFBFC] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)]/40"
      >
        <span
          className={cn("size-2 flex-none rounded-full", SEVERITY_DOT[flag.severity])}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-medium text-[var(--ink-1)]">{label}</div>
          <div className="mt-0.5 truncate text-[11.5px] text-[var(--ink-3)]">
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
        <Chevron className="size-4 flex-none text-[var(--ink-4)]" aria-hidden />
      </button>

      {expanded && (
        <div className="ml-5 border-l-2 border-[var(--border)] pl-4 pb-4 text-[12.5px] text-[var(--ink-2)]">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
            <dt className="text-[var(--ink-3)]">Правило</dt>
            <dd className="font-mono text-[11.5px]">{flag.rule_id}</dd>

            <dt className="text-[var(--ink-3)]">Severity</dt>
            <dd>{SEVERITY_LABEL[flag.severity]}</dd>

            <dt className="text-[var(--ink-3)]">Сообщение</dt>
            <dd>{flag.message}</dd>

            {evidenceEntries.length > 0 && (
              <>
                <dt className="self-start text-[var(--ink-3)]">Evidence</dt>
                <dd>
                  <ul className="space-y-0.5">
                    {evidenceEntries.map(([k, v]) => (
                      <li key={k} className="font-mono text-[11.5px]">
                        <span className="text-[var(--ink-3)]">{k}:</span>{" "}
                        <span className="text-[var(--ink-1)]">
                          {formatEvidenceCell(v)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </dd>
              </>
            )}
          </dl>
        </div>
      )}
    </li>
  );
}

// Достаём «главное число» из evidence по rule_id, чтобы показать его в pill.
// Числовые evidence приходят как `Decimal`-строки (ADR-0007), без округления
// дают хвост из 18+ цифр в UI — поэтому всё через formatEvidenceNumber.
function renderEvidenceValue(flag: RedFlagDto): string | null {
  const e = flag.evidence;
  switch (flag.rule_id) {
    case "LOAN_TO_REVENUE_RATIO": {
      const v = formatEvidenceNumber(e.ratio);
      return v ? `${v}x` : null;
    }
    case "TAX_PAYMENT_DELAYS": {
      const v = formatEvidenceNumber(e.yoy_pct);
      return v ? `${v}%` : null;
    }
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

function formatEvidenceNumber(raw: unknown): string | null {
  if (typeof raw !== "string" && typeof raw !== "number") return null;
  const n = typeof raw === "number" ? raw : parseFloat(raw);
  if (!Number.isFinite(n)) return null;
  return n.toFixed(2).replace(".", ",");
}

// CA-050: универсальное отображение evidence-значения в раскрытой строке.
// Числовые Decimal-строки округляем до 2 знаков (как в pill); прочее — as-is.
function formatEvidenceCell(raw: unknown): string {
  if (raw === null || raw === undefined) return "—";
  if (typeof raw === "boolean") return raw ? "да" : "нет";
  if (typeof raw === "number") return raw.toFixed(2).replace(".", ",");
  if (typeof raw === "string") {
    // Числовая строка → округляем; остальное (год, имя, ИНН) — без изменений.
    const n = parseFloat(raw);
    if (Number.isFinite(n) && /^-?\d+(?:\.\d+)?$/.test(raw)) {
      return n.toFixed(2).replace(".", ",");
    }
    return raw;
  }
  return JSON.stringify(raw);
}

function pluralFlags(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "сигналов";
  if (mod10 === 1) return "сигнал";
  if (mod10 >= 2 && mod10 <= 4) return "сигнала";
  return "сигналов";
}
