"use client";

// Phase 7: Step 2 design statement. Section card pattern (Phase 6 — icon-tile +
// gradient header + counter), source-trail hints под каждым полем, Annual block
// разбит на 3 flat-группы (Налоги | НДС | Баланс).
//
// Source-trail state (CA-DS21 — 3-state):
//   • auto         — парсер положил значение AND current === parsed.
//   • auto-edited  — парсер положил, пользователь поправил (current !== parsed).
//                    Info-tone (синий) borderbar, нейтральный suffix.
//   • manual       — парсер не трогал, ввод руками.
//   • manual-required (special) — taxesPaid*: PROFIT_TAX-парсер заполняет
//     только если бухгалтер приложил Расчёт налога на прибыль. Без файла —
//     поля руками. Хинт даёт повышенный визуальный вес чтобы аналитик понимал
//     «это не пропущенный autofill — это by design».
//   • waiting      — поле пустое, парсер не трогал.

import {
  Calculator,
  CheckCircle2,
  FileText,
  Pencil,
  Scale,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { CounterChip, SectionCard } from "@/components/section-card";
import { cn } from "@/lib/utils";

import { useSourceTrail } from "../hooks/use-source-trail";
import {
  computeDebtToAssets,
  computeEquity,
  digitsOnly,
  formatUzs,
  parseAmount,
} from "../lib/finance";
import type { FormValues } from "../schema";

import { FinancialTable } from "./financial-table";
import { ParsedFilesDropzone } from "./parsed-files-dropzone";
import { SoliqUpload } from "./soliq-upload";

// Маппинг form-path → ключ в sourceTrail (CA-027 + CA-037 + CA-041).
// Если поле в map — оно пришло из xltx-парсера; иначе manual.
const SOURCE_KEYS: Record<string, { key: string; sourceTag: string }> = {
  "step2.revenue.y2024.annual": { key: "revenue_2024", sourceTag: "FORM_2" },
  "step2.revenue.y2025.annual": { key: "revenue_2025", sourceTag: "FORM_2" },
  "step2.netProfit.y2024.annual": { key: "net_profit_2024", sourceTag: "FORM_2" },
  "step2.netProfit.y2025.annual": { key: "net_profit_2025", sourceTag: "FORM_2" },
  "step2.vatDeclared": { key: "vat_declared_2025", sourceTag: "VAT_DECLARATION" },
  "step2.totalAssets": { key: "form1.assets_total", sourceTag: "FORM_1" },
  "step2.totalLiabilities": { key: "form1.liabilities_total", sourceTag: "FORM_1" },
};

export function Step2Financials() {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="space-y-[18px]">
      <ParsedFilesDropzone />
      <SoliqUpload />

      <SectionCard
        icon={<TrendingUp className="size-[18px]" />}
        title={t("s2_revenue_title")}
        sub={t("s2_revenue_sub")}
        aux={<RevenueCounter />}
      >
        <FinancialTable basePath="step2.revenue" variant="revenue" />
      </SectionCard>

      <SectionCard
        icon={<Wallet className="size-[18px]" />}
        title={t("s2_profit_title")}
        sub={t("s2_profit_sub")}
        aux={<ProfitCounter />}
      >
        <FinancialTable basePath="step2.netProfit" variant="netProfit" />
      </SectionCard>

      <SectionCard
        icon={<Calculator className="size-[18px]" />}
        title={t("s2_annual_title")}
        sub={t("s2_annual_sub")}
      >
        <AnnualBlock />
      </SectionCard>
    </div>
  );
}

function countYearsWithValue(
  q: { q1: string; q2: string; q3: string; q4: string; annual?: string } | undefined,
): number {
  if (!q) return 0;
  const hasAnnual = digitsOnly(q.annual ?? "").length > 0;
  const hasAnyQuarter = [q.q1, q.q2, q.q3, q.q4].some(
    (v) => digitsOnly(v).length > 0,
  );
  return hasAnnual || hasAnyQuarter ? 1 : 0;
}

function RevenueCounter() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const revenue = useWatch({ control, name: "step2.revenue" });
  const filled =
    countYearsWithValue(revenue?.y2023) +
    countYearsWithValue(revenue?.y2024) +
    countYearsWithValue(revenue?.y2025);
  return <CounterChip filled={filled} total={3} eyebrow={t("s2_counter_filled")} />;
}

function ProfitCounter() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const profit = useWatch({ control, name: "step2.netProfit" });
  const filled =
    countYearsWithValue(profit?.y2023) +
    countYearsWithValue(profit?.y2024) +
    countYearsWithValue(profit?.y2025);
  return <CounterChip filled={filled} total={3} eyebrow={t("s2_counter_filled")} />;
}

// ─────────── Annual block: 3 flat groups (Налоги | НДС | Баланс) ─────────

function AnnualBlock() {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="flex flex-col gap-[18px]">
      <AnnualGroup
        icon={<Receipt className="size-[14px]" />}
        titleKey="s2_annual_group_taxes_title"
        subKey="s2_annual_group_taxes_sub"
      >
        <UzsRow
          fieldName="step2.taxesPaid23"
          labelKey="s2_taxes_y23_label"
          ariaLabelKey="s2_taxes_y23_label"
          required={false}
          forceManualRequired
        />
        <UzsRow
          fieldName="step2.taxesPaid24"
          labelKey="s2_taxes_y24_label"
          ariaLabelKey="s2_taxes_y24_label"
          required={false}
          forceManualRequired
        />
        <UzsRow
          fieldName="step2.taxesPaid25"
          labelKey="s2_taxes_y25_label"
          ariaLabelKey="s2_taxes_y25_label"
          required
          forceManualRequired
        />
      </AnnualGroup>

      <AnnualGroup
        icon={<FileText className="size-[14px]" />}
        titleKey="s2_annual_group_vat_title"
        subKey="s2_annual_group_vat_sub"
      >
        <UzsRow
          fieldName="step2.vatDeclared"
          labelKey="s2_vat_label"
          ariaLabelKey="s2_vat_label"
          required
        />
      </AnnualGroup>

      <AnnualGroup
        icon={<Scale className="size-[14px]" />}
        titleKey="s2_annual_group_balance_title"
        subKey="s2_annual_group_balance_sub"
        last
      >
        <UzsRow
          fieldName="step2.totalAssets"
          labelKey="s2_assets_label"
          ariaLabelKey="s2_assets_label"
          required
        />
        <UzsRow
          fieldName="step2.totalLiabilities"
          labelKey="s2_liabs_label"
          ariaLabelKey="s2_liabs_label"
          required
        />
        <UzsRow
          fieldName="step2.inventoryEnd25"
          labelKey="s2_inventory_label"
          ariaLabelKey="s2_inventory_label"
          required={false}
        />
        <BalanceComputed />
      </AnnualGroup>

      <p className="-mt-2 text-[11.5px] leading-[1.55] text-[var(--ink-4)]">
        {t("s2_annual_footer_note")}
      </p>
    </div>
  );
}

// Receipt icon — local (lucide Receipt requires v0.300+; we have older subset).
function Receipt({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z" />
      <path d="M8 7h8" />
      <path d="M8 11h8" />
      <path d="M8 15h6" />
    </svg>
  );
}

function AnnualGroup({
  icon,
  titleKey,
  subKey,
  children,
  last,
}: {
  icon: ReactNode;
  titleKey: string;
  subKey: string;
  children: ReactNode;
  last?: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-[18px] md:grid-cols-[210px_1fr]",
        !last && "border-b border-dashed border-[var(--border)] pb-[18px]",
      )}
    >
      <div>
        <div className="flex items-center gap-2">
          <div className="grid size-[26px] place-items-center rounded-[7px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]">
            {icon}
          </div>
          <div className="text-[12.5px] font-bold tracking-[0.06em] text-[var(--ink-1)] uppercase">
            {t(titleKey)}
          </div>
        </div>
        <div className="mt-2 text-[11.5px] leading-[1.55] text-[var(--ink-4)]">
          {t(subKey)}
        </div>
      </div>
      <div className="flex flex-col gap-[12px]">{children}</div>
    </div>
  );
}

// ─────────── UZS row (annual field) + source-trail hint ─────────────────

type UzsFieldName =
  | "step2.vatDeclared"
  | "step2.taxesPaid23"
  | "step2.taxesPaid24"
  | "step2.taxesPaid25"
  | "step2.totalAssets"
  | "step2.totalLiabilities"
  | "step2.inventoryEnd25";

function UzsRow({
  fieldName,
  labelKey,
  ariaLabelKey,
  required,
  forceManualRequired,
}: {
  fieldName: UzsFieldName;
  labelKey: string;
  ariaLabelKey: string;
  required: boolean;
  forceManualRequired?: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  const { control, formState } = useFormContext<FormValues>();
  const errorMsg = errorForPath(formState.errors, fieldName);
  const touched = touchedForPath(formState.touchedFields, fieldName);
  const visibleError = touched ? errorMsg : undefined;
  const state = useFieldSourceState(fieldName, { forceManualRequired });

  return (
    <div className="grid grid-cols-[100px_1fr] items-start gap-[14px]">
      <label
        className="pt-[10px] text-right text-[12.5px] font-medium text-[var(--ink-2)]"
        htmlFor={ariaLabelKey}
      >
        {t(labelKey)}
        {required ? (
          <span className="ml-0.5 font-semibold text-[var(--state-bad-fg)]">
            *
          </span>
        ) : null}
      </label>
      <div className="flex flex-col gap-[6px]">
        <Controller
          control={control}
          name={fieldName}
          render={({ field }) => (
            <UzsInputShell state={state} invalid={Boolean(visibleError)}>
              <input
                id={ariaLabelKey}
                ref={field.ref}
                value={formatUzs((field.value as string) ?? "")}
                onBlur={field.onBlur}
                onChange={(e) => field.onChange(digitsOnly(e.target.value))}
                inputMode="numeric"
                placeholder="0"
                aria-invalid={Boolean(visibleError) || undefined}
                className={cn(
                  "h-10 w-full rounded-l-[9px] border border-r-0 border-[var(--border-strong)] bg-[var(--surface)] px-3 text-right font-mono text-[14px] text-[var(--ink-1)] outline-none transition-colors placeholder:text-[var(--ink-4)] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_var(--brand-primary-ring)]",
                  visibleError &&
                    "border-[var(--state-bad-fg)] focus:border-[var(--state-bad-fg)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
                )}
              />
            </UzsInputShell>
          )}
        />
        {visibleError ? (
          <div className="text-[11.5px] text-[var(--state-bad-fg)]">
            {visibleError}
          </div>
        ) : (
          <SourceHint state={state} />
        )}
      </div>
    </div>
  );
}

export function UzsInputShell({
  state,
  invalid,
  children,
}: {
  state: SourceState;
  invalid: boolean;
  children: ReactNode;
}) {
  return (
    <div className="relative flex items-stretch">
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute top-0 bottom-0 left-0 z-[1] w-[3px] rounded-l-[9px]",
          state === "auto" && "bg-[var(--state-ok-fg)]",
          state === "auto-edited" && "bg-[var(--state-info-fg)]",
          state === "manual-required" &&
            "bg-[var(--state-warn-fg)] opacity-60",
        )}
      />
      <div className="flex flex-1 items-stretch [&>input]:rounded-r-none [&>input]:border-r-0">
        {children}
      </div>
      <div
        className={cn(
          "grid place-items-center rounded-r-[9px] border border-l-0 px-3 font-mono text-[11.5px] font-semibold tracking-[0.04em]",
          state === "auto"
            ? "border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]"
            : invalid
              ? "border-[var(--state-bad-fg)] bg-[var(--state-bad-bg)] text-[var(--state-bad-fg)]"
              : "border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--ink-3)]",
        )}
      >
        UZS
      </div>
    </div>
  );
}

// ─────────── Source-trail state + hint UI ────────────────────────────────

export type SourceState =
  | "auto"
  | "auto-edited"
  | "manual"
  | "manual-required"
  | "waiting";

export function useFieldSourceState(
  fieldName: string,
  opts: { forceManualRequired?: boolean } = {},
): SourceState {
  const { sourceTrail, parsedValues } = useSourceTrail();
  const { control } = useFormContext<FormValues>();
  // useWatch на конкретный путь, чтобы re-render только при изменении этого
  // поля, а не всей формы. Cast `as never` — react-hook-form требует
  // FieldPath<FormValues>; наши UzsFieldName уже валидные пути.
  const value = useWatch({ control, name: fieldName as never });
  const current = digitsOnly((value as string) ?? "");
  const has = current.length > 0;

  if (opts.forceManualRequired) return "manual-required";

  // CA-DS21: если парсер положил значение (parsedValues[fieldName]) —
  // сравниваем с current. Совпало → auto, не совпало → auto-edited.
  // Случай «парсер положил, потом очищено» (current === "") тоже
  // auto-edited: пользователь явно убрал autofill.
  const parsed = parsedValues[fieldName];
  if (parsed !== undefined) {
    return current === parsed ? "auto" : "auto-edited";
  }

  // Парсер не трогал — fallback на sourceTrail (на случай если sourceTrail
  // получит данные из другого источника не через ParsedFilesDropzone).
  const mapping = SOURCE_KEYS[fieldName];
  if (mapping && sourceTrail[mapping.key]) return "auto";
  if (has) return "manual";
  return "waiting";
}

export function SourceHint({
  state,
  fieldName,
}: {
  state: SourceState;
  fieldName?: string;
}) {
  const t = useTranslations("accountant.manual_input");
  const mapping = fieldName ? SOURCE_KEYS[fieldName] : undefined;
  const sourceTag = mapping?.sourceTag;

  if (state === "auto") {
    return (
      <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--state-ok-fg)]">
        <CheckCircle2 className="size-[11px] flex-none" />
        <span>{t("s2_source_auto")}</span>
        {sourceTag ? <SourceTag tone="ok">{sourceTag}</SourceTag> : null}
        <span className="text-[10.5px] text-[var(--ink-4)]">
          · {t("s2_source_auto_hint")}
        </span>
      </div>
    );
  }
  if (state === "auto-edited") {
    return (
      <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--state-info-fg)]">
        <Pencil className="size-[11px] flex-none" />
        <span>{t("s2_source_auto_edited")}</span>
        {sourceTag ? <SourceTag tone="info">{sourceTag}</SourceTag> : null}
        <span className="text-[10.5px] text-[var(--ink-4)]">
          · {t("s2_source_auto_edited_hint")}
        </span>
      </div>
    );
  }
  if (state === "manual-required") {
    return (
      <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--state-warn-fg)]">
        <Pencil className="size-[11px] flex-none" />
        <span>{t("s2_source_manual_required")}</span>
        <span className="text-[10.5px]">
          · {t("s2_source_manual_required_hint")}
        </span>
      </div>
    );
  }
  if (state === "manual") {
    return (
      <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--ink-4)]">
        <Pencil className="size-[11px] flex-none" />
        <span>{t("s2_source_manual")}</span>
      </div>
    );
  }
  // waiting
  return (
    <div className="inline-flex items-center gap-[5px] text-[11px] leading-[1.3] font-medium text-[var(--ink-4)]">
      <span
        aria-hidden
        className="grid size-[11px] place-items-center rounded-full border border-current text-[8px]"
      >
        ?
      </span>
      <span>{t("s2_source_waiting")}</span>
      {sourceTag ? <SourceTag tone="muted">{sourceTag}</SourceTag> : null}
    </div>
  );
}

function SourceTag({
  tone,
  children,
}: {
  tone: "ok" | "muted" | "info";
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "rounded-[3px] px-[5px] py-px font-mono text-[10.5px] font-bold tracking-[0.03em]",
        tone === "ok" && "bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
        tone === "info" &&
          "bg-[var(--state-info-bg)] text-[var(--state-info-fg)]",
        tone === "muted" && "bg-[var(--surface-2)] text-[var(--ink-3)]",
      )}
    >
      {children}
    </span>
  );
}

// ─────────── Balance computed (D/A + Equity) inside group ────────────────

function BalanceComputed() {
  const t = useTranslations("accountant.manual_input");
  const { control } = useFormContext<FormValues>();
  const assets = useWatch({ control, name: "step2.totalAssets" });
  const liabilities = useWatch({ control, name: "step2.totalLiabilities" });

  const a = parseAmount((assets as string) ?? "");
  const l = parseAmount((liabilities as string) ?? "");
  const da = computeDebtToAssets(l, a);
  const equity = computeEquity(a, l);
  const hasData = a > 0;

  const daTone: "good" | "warn" | "bad" | "neutral" = !hasData
    ? "neutral"
    : da < 0.55
      ? "good"
      : da < 0.75
        ? "warn"
        : "bad";

  return (
    <div className="mt-2 grid grid-cols-2 divide-x divide-[var(--border)] rounded-[10px] border border-dashed border-[var(--border-strong)] bg-[var(--surface-2)] px-[14px] py-[12px]">
      <ComputedTile
        label={t("s2_da_label")}
        sub={t("s2_da_sub")}
        value={hasData ? da.toFixed(2).replace(".", ",") : "—"}
        tone={daTone}
      />
      <ComputedTile
        label={t("s2_equity_label")}
        sub={t("s2_equity_sub")}
        value={hasData && equity !== 0 ? formatUzs(String(Math.abs(equity))) : "—"}
        suffix={hasData && equity !== 0 ? "UZS" : undefined}
        tone={hasData && equity < 0 ? "bad" : "neutral"}
      />
    </div>
  );
}

function ComputedTile({
  label,
  sub,
  value,
  suffix,
  tone,
}: {
  label: string;
  sub: string;
  value: string;
  suffix?: string;
  tone: "good" | "warn" | "bad" | "neutral";
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 px-3 first:pl-0 last:pr-0">
      <div>
        <div className="text-[11px] font-bold tracking-[0.06em] text-[var(--ink-3)] uppercase">
          {label}
        </div>
        <div className="mt-[2px] text-[10.5px] text-[var(--ink-4)]">{sub}</div>
      </div>
      <div
        className={cn(
          "font-mono text-[14px] font-bold whitespace-nowrap",
          tone === "good" && "text-[var(--state-ok-fg)]",
          tone === "warn" && "text-[var(--state-warn-fg)]",
          tone === "bad" && "text-[var(--state-bad-fg)]",
          tone === "neutral" && "text-[var(--ink-1)]",
        )}
      >
        {value}
        {suffix ? (
          <span className="ml-1 text-[10.5px] font-medium text-[var(--ink-4)]">
            {suffix}
          </span>
        ) : null}
      </div>
    </div>
  );
}

// ─────────── react-hook-form errors helpers ──────────────────────────────

function errorForPath(
  errors: Record<string, unknown>,
  path: string,
): string | undefined {
  const parts = path.split(".");
  let cur: unknown = errors;
  for (const part of parts) {
    if (cur === null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  if (cur && typeof cur === "object" && "message" in cur) {
    const msg = (cur as { message?: unknown }).message;
    return typeof msg === "string" ? msg : undefined;
  }
  return undefined;
}

function touchedForPath(
  touched: Record<string, unknown>,
  path: string,
): boolean {
  const parts = path.split(".");
  let cur: unknown = touched;
  for (const part of parts) {
    if (cur === null || typeof cur !== "object") return false;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur === true;
}
