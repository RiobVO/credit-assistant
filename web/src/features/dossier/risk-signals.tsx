"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { CounterChip, SectionCard } from "@/components/section-card";
import type { RedFlagDto, Severity } from "@/lib/api";
import { cn } from "@/lib/utils";

const SEVERITY_DOT: Record<Severity, string> = {
  low: "bg-[var(--state-ok-fg)]",
  medium: "bg-[var(--state-warn-fg)]",
  high: "bg-[var(--state-bad-fg)]",
  // critical — тот же fg + ring через box-shadow, чтобы отличать от high.
  critical: "bg-[var(--state-bad-fg)] shadow-[0_0_0_3px_var(--state-bad-bg)]",
};

const SEVERITY_PILL: Record<Severity, string> = {
  low: "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
  medium:
    "border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] text-[var(--state-warn-fg)]",
  high: "border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]",
  critical:
    "border-[var(--state-bad-fg)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]",
};

// CA-050: accordion-rows + actual rules_evaluated count из API
// (вместо хардкода 17 — реестр после CA-049 содержит 19 правил).
//
// Phase 9: SectionCard shell + CounterChip в aux ({count}/{evaluated}), severity
// pills через semantic state-tokens, hover на surface-2 (не hardcode #FAFBFC),
// accordion expanded-block — чистый border-l-2 brand-primary без gradient (был
// rich для evidence-dl, см. Phase 9 reality-check).
export function RiskSignals({
  flags,
  rulesEvaluated,
}: {
  flags: RedFlagDto[];
  rulesEvaluated: number;
}) {
  const t = useTranslations("dossier.risk");
  const counter = (
    <CounterChip
      filled={flags.length}
      total={rulesEvaluated}
      eyebrow={t("counter_eyebrow")}
    />
  );
  return (
    <SectionCard
      title={t("title")}
      sub={t("subtitle", { count: flags.length, evaluated: rulesEvaluated })}
      aux={counter}
    >
      {flags.length === 0 ? (
        <div className="px-2 py-8 text-center text-[13px] text-[var(--ink-3)]">
          {t("empty")}
        </div>
      ) : (
        <ul className="-mx-[22px] -my-[22px] divide-y divide-[var(--border)]">
          {flags.map((f) => (
            <SignalRow key={`${f.rule_id}-${f.detected_at}`} flag={f} />
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

function SignalRow({ flag }: { flag: RedFlagDto }) {
  const t = useTranslations("dossier.risk");
  const [expanded, setExpanded] = useState(false);
  // t() returns rule label, fall back to raw rule_id если ключа нет.
  const ruleKey = `rule_${flag.rule_id}` as const;
  const label = t.has(ruleKey) ? t(ruleKey) : flag.rule_id;
  const value = renderEvidenceValue(flag);
  const Chevron = expanded ? ChevronDown : ChevronRight;
  const evidenceEntries = Object.entries(flag.evidence ?? {});
  const severityLabel = t(`severity_${flag.severity}`);

  return (
    <li className="px-[22px]">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-3 py-3 text-left transition-colors hover:bg-[var(--surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary-ring)]"
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
        <div className="mb-3 ml-5 rounded-r-[9px] border-l-2 border-[var(--brand-primary)] bg-[var(--surface-2)] px-4 py-3 text-[12.5px] text-[var(--ink-2)]">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
            <dt className="text-[var(--ink-3)]">{t("field_rule")}</dt>
            <dd className="font-mono text-[11.5px]">{flag.rule_id}</dd>

            <dt className="text-[var(--ink-3)]">{t("field_severity")}</dt>
            <dd>{severityLabel}</dd>

            <dt className="text-[var(--ink-3)]">{t("field_message")}</dt>
            <dd>{flag.message}</dd>

            {evidenceEntries.length > 0 && (
              <>
                <dt className="self-start text-[var(--ink-3)]">{t("field_evidence")}</dt>
                <dd>
                  <ul className="space-y-0.5">
                    {evidenceEntries.map(([k, v]) => (
                      <li key={k} className="font-mono text-[11.5px]">
                        <span className="text-[var(--ink-3)]">{k}:</span>{" "}
                        <span className="text-[var(--ink-1)]">
                          {formatEvidenceCell(v, t("evidence_yes"), t("evidence_no"))}
                        </span>
                      </li>
                    ))}
                  </ul>
                </dd>
              </>
            )}
          </dl>
          {flag.source ? (
            <div className="mt-2 border-t border-dashed border-[var(--border)] pt-2 text-[11.5px] text-[var(--ink-4)]">
              {flag.source}
            </div>
          ) : null}
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
function formatEvidenceCell(raw: unknown, yes: string, no: string): string {
  if (raw === null || raw === undefined) return "—";
  if (typeof raw === "boolean") return raw ? yes : no;
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
