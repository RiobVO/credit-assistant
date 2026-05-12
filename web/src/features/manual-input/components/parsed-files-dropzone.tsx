"use client";

// CA-027: Multi-file автозаполнение Step 2 wizard.
// Принимает несколько xltx (FORM_2 + VAT_DECLARATION), POST /api/manual-input/parse-files,
// после успешного ответа — setValue в поля формы (revenue.annual, netProfit.annual,
// vatDeclared) + сводка автозаполненных полей с указанием источника.
//
// Read-only chip per cell + «не нашли файл — ввести вручную» override — отложено
// в TODO[CA-031]: требует invasive рефактора всех ячеек формы. Сейчас autofill
// работает как обычный setValue — поля редактируемые, пользователь видит источники
// в сводной карточке и может править вручную, если что-то распознано неверно.

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, FileText, TriangleAlert, Trash2, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { type FieldPath, useFormContext } from "react-hook-form";

import { ApiError, type ParsedFinancialsDto, parseManualInputFiles } from "@/lib/api";
import { cn } from "@/lib/utils";

import { useSourceTrail } from "../hooks/use-source-trail";
import type { FormValues } from "../schema";

type Translator = ReturnType<typeof useTranslations>;

type SetValueFn = (
  path: FieldPath<FormValues>,
  value: string,
  opts?: { shouldValidate?: boolean },
) => void;

const ACCEPT = ".xltx,application/vnd.ms-excel.template.macroEnabled.12";
const MAX_FILES = 10;
const KNOWN_YEARS = [2023, 2024, 2025] as const;

type Source = { fieldLabel: string; year?: number; sourceLabel: string };

export function ParsedFilesDropzone() {
  const t = useTranslations("accountant.manual_input");
  const { setValue } = useFormContext<FormValues>();
  const { mergeSourceTrail } = useSourceTrail();
  const [files, setFiles] = useState<File[]>([]);
  const [autofilled, setAutofilled] = useState<Source[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: () => parseManualInputFiles(files),
    onSuccess: (data) => {
      const filled = applyToForm(data, setValue, t);
      setAutofilled(filled);
      setWarnings(data.parse_warnings ?? []);
      // CA-035: source_trail в context, чтобы Checklist (Шаг 3) знал какие
      // парсеры дали данные. Merge, не replace — каждый upload добавляет
      // свои ключи, ранее загруженные файлы остаются известны.
      mergeSourceTrail(data.source_trail ?? {});
    },
  });

  const onAddFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    setFiles((prev) => {
      const next = [...prev];
      for (const f of Array.from(incoming)) {
        if (next.length >= MAX_FILES) break;
        if (next.some((x) => x.name === f.name && x.size === f.size)) continue;
        next.push(f);
      }
      return next;
    });
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const canSubmit = files.length > 0 && !mutation.isPending;
  const errorMessage =
    mutation.error instanceof ApiError
      ? formatApiError(mutation.error, t)
      : mutation.error
        ? t("dropzone_parse_error")
        : null;

  return (
    <section className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--border)] px-[22px] py-[18px]">
        <Upload className="size-4 text-[var(--brand-primary)]" />
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ink-1)]">
            {t("dropzone_title")}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {t("dropzone_sub")}
          </p>
        </div>
      </header>

      <div className="space-y-4 p-[22px]">
        <DropZone onSelect={onAddFiles} inputRef={inputRef} />

        {files.length > 0 && (
          <ul className="divide-y divide-[var(--border)] rounded-md border border-[var(--border)]">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-2 px-3 py-2">
                <FileText className="size-4 flex-none text-[var(--ink-4)]" />
                <span className="flex-1 truncate text-[13px] text-[var(--ink-2)]">
                  {f.name}
                </span>
                <span className="font-mono text-[11.5px] text-[var(--ink-4)]">
                  {(f.size / 1024).toFixed(0)} КБ
                </span>
                <button
                  type="button"
                  aria-label={t("dropzone_remove_aria", { name: f.name })}
                  onClick={() => removeFile(i)}
                  className="rounded p-1 text-[var(--ink-4)] transition-colors hover:bg-[#FCE7E5] hover:text-[var(--state-bad-fg)]"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center justify-between">
          <span className="text-[12px] text-[var(--ink-3)]">
            {files.length === 0
              ? t("dropzone_files_hint_empty", { max: MAX_FILES })
              : t("dropzone_files_hint_count", { count: files.length })}
          </span>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => mutation.mutate()}
            className={cn(
              "inline-flex h-[38px] items-center gap-2 rounded-md px-5 text-[13.5px] font-semibold transition-colors",
              canSubmit
                ? "bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-primary-hover)]"
                : "cursor-not-allowed bg-[#E5E9EF] text-[var(--ink-4)]",
            )}
          >
            {mutation.isPending ? t("dropzone_submitting") : t("dropzone_submit")}
          </button>
        </div>

        {errorMessage && (
          <div className="flex items-start gap-2 rounded-md border border-[#F2BCBA] bg-[#FCE7E5] px-3 py-2 text-[12.5px] text-[var(--state-bad-fg)]">
            <TriangleAlert className="size-4 flex-none" />
            <span>{errorMessage}</span>
          </div>
        )}

        {autofilled.length > 0 && <AutofilledSummary entries={autofilled} />}

        {warnings.length > 0 && <WarningsBlock warnings={warnings} />}
      </div>
    </section>
  );
}

function DropZone({
  onSelect,
  inputRef,
}: {
  onSelect: (f: FileList | null) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const t = useTranslations("accountant.manual_input");
  const [over, setOver] = useState(false);
  return (
    <label
      onDragEnter={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        onSelect(e.dataTransfer.files);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-md border-2 border-dashed px-6 py-7 transition-colors",
        over
          ? "border-[var(--brand-primary)] bg-[#F4F8FF]"
          : "border-[var(--border-strong)] bg-[#FAFBFC] hover:bg-[#F4F6F9]",
      )}
    >
      <Upload className="size-5 text-[var(--ink-3)]" />
      <span className="text-[13px] font-medium text-[var(--ink-2)]">
        {t("dropzone_drag_text")}
      </span>
      <span className="text-[11.5px] text-[var(--ink-3)]">
        {t("dropzone_drag_sub")}
      </span>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        className="sr-only"
        onChange={(e) => onSelect(e.target.files)}
      />
    </label>
  );
}

function AutofilledSummary({ entries }: { entries: Source[] }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="rounded-md border border-[#BFE2D2] bg-[var(--state-ok-bg)] px-3 py-2.5">
      <div className="mb-1.5 flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--state-ok-fg)]">
        <CheckCircle2 className="size-4" />
        {t("dropzone_autofilled_heading", { count: entries.length })}
      </div>
      <ul className="space-y-1 text-[12px] text-[var(--ink-2)]">
        {entries.map((e, i) => (
          <li key={i} className="flex items-baseline gap-2">
            <span className="font-medium">{e.fieldLabel}</span>
            {e.year ? <span className="text-[var(--ink-3)]">{e.year}</span> : null}
            <span className="text-[11.5px] text-[var(--ink-3)]">
              {t("dropzone_source_prefix", { source: e.sourceLabel })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WarningsBlock({ warnings }: { warnings: string[] }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <details className="rounded-md border border-[#F1D9A6] bg-[#FFF6E5] px-3 py-2">
      <summary className="cursor-pointer text-[12.5px] font-semibold text-[var(--state-warn-fg)]">
        {t("dropzone_warnings_summary", { count: warnings.length })}
      </summary>
      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-[11.5px] text-[var(--ink-2)]">
        {warnings.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
      </ul>
    </details>
  );
}

function formatApiError(err: ApiError, t: Translator): string {
  if (typeof err.body === "object" && err.body !== null && "detail" in err.body) {
    return String((err.body as { detail: unknown }).detail);
  }
  return t("dropzone_http_error", { status: err.status });
}

/**
 * Hydrate form fields from parsed response.
 * Возвращает список заполненных полей для сводки.
 *
 * Целит в `step2.{revenue,netProfit}.yXXXX.annual` и `step2.vatDeclared`.
 * Десятичные .00 у Decimal-строки урезаются (UZS-форма не показывает копейки).
 */
function applyToForm(
  data: ParsedFinancialsDto,
  setValue: SetValueFn,
  t: Translator,
): Source[] {
  const filled: Source[] = [];
  const sourceFile = t("dropzone_source_fallback_file");
  const sourceAutofill = t("dropzone_source_fallback_autofill");

  const setAnnual = (
    section: "revenue" | "netProfit",
    year: number,
    value: string,
    sourceLabel: string,
    fieldLabel: string,
  ) => {
    if (!KNOWN_YEARS.includes(year as (typeof KNOWN_YEARS)[number])) return;
    const path =
      `step2.${section}.y${year}.annual` as FieldPath<FormValues>;
    setValue(path, normalizeDigits(value), { shouldValidate: true });
    filled.push({ fieldLabel, year, sourceLabel });
  };

  for (const [year, value] of Object.entries(data.revenue_by_year)) {
    setAnnual(
      "revenue",
      Number(year),
      value,
      data.source_trail[`revenue_${year}`] ?? sourceFile,
      t("dropzone_field_revenue_annual"),
    );
  }
  for (const [year, value] of Object.entries(data.net_profit_by_year)) {
    setAnnual(
      "netProfit",
      Number(year),
      value,
      data.source_trail[`net_profit_${year}`] ?? sourceFile,
      t("dropzone_field_profit_annual"),
    );
  }
  // VAT — единственный «годовой» annual в форме, привязан к latest year (2025).
  // Если в DTO есть 2025 — кладём в step2.vatDeclared. Прочие годы пока игнор
  // (форма поддерживает один период).
  if (data.vat_declared_by_year["2025"]) {
    setValue("step2.vatDeclared", normalizeDigits(data.vat_declared_by_year["2025"]), {
      shouldValidate: true,
    });
    filled.push({
      fieldLabel: t("dropzone_field_vat_2025"),
      sourceLabel: data.source_trail["vat_declared_2025"] ?? sourceFile,
    });
  }

  // CA-041: FORM_1 → assets/liabilities на конец отчётного периода (column E).
  if (data.assets_total) {
    setValue("step2.totalAssets", normalizeDigits(data.assets_total), {
      shouldValidate: true,
    });
    filled.push({
      fieldLabel: t("dropzone_field_assets_end"),
      sourceLabel: data.source_trail["form1.assets_total"] ?? "FORM_1",
    });
  }
  if (data.liabilities_total) {
    setValue("step2.totalLiabilities", normalizeDigits(data.liabilities_total), {
      shouldValidate: true,
    });
    filled.push({
      fieldLabel: t("dropzone_field_liabs_end"),
      sourceLabel: data.source_trail["form1.liabilities_total"] ?? "FORM_1",
    });
  }

  // CA-037: hidden поля для EBIT/ROE/Debt-to-EBIT. UI inputs пока не
  // показываются; данные доходят до backend через _form-mapper. Источник —
  // FORM_2 (PBT, interest) для current+prior year, FORM_1 (equity, total_debt,
  // balance period_start) для current year.
  const ca037Hidden: Array<{
    field: FieldPath<FormValues>;
    value: string | null;
    label: string;
    sourceKey: string;
  }> = [
    {
      field: "step2.profitBeforeTax25",
      value: data.profit_before_tax_by_year?.["2025"] ?? null,
      label: t("dropzone_field_pbt", { year: 2025 }),
      sourceKey: "profit_before_tax_2025",
    },
    {
      field: "step2.profitBeforeTax24",
      value: data.profit_before_tax_by_year?.["2024"] ?? null,
      label: t("dropzone_field_pbt", { year: 2024 }),
      sourceKey: "profit_before_tax_2024",
    },
    {
      field: "step2.interestExpense25",
      value: data.interest_expense_by_year?.["2025"] ?? null,
      label: t("dropzone_field_interest", { year: 2025 }),
      sourceKey: "interest_expense_2025",
    },
    {
      field: "step2.interestExpense24",
      value: data.interest_expense_by_year?.["2024"] ?? null,
      label: t("dropzone_field_interest", { year: 2024 }),
      sourceKey: "interest_expense_2024",
    },
    {
      field: "step2.equityEnd25",
      value: data.equity_period_end,
      label: t("dropzone_field_equity_end"),
      sourceKey: "form1.equity",
    },
    {
      field: "step2.equityStart25",
      value: data.equity_period_start,
      label: t("dropzone_field_equity_start"),
      sourceKey: "form1.equity_period_start",
    },
    {
      field: "step2.totalDebtEnd25",
      value: data.total_debt_period_end,
      label: t("dropzone_field_debt_end"),
      sourceKey: "form1.total_debt",
    },
    {
      field: "step2.totalDebtStart25",
      value: data.total_debt_period_start,
      label: t("dropzone_field_debt_start"),
      sourceKey: "form1.total_debt_period_start",
    },
    {
      field: "step2.assetsStart25",
      value: data.assets_total_period_start,
      label: t("dropzone_field_assets_start"),
      sourceKey: "form1.assets_total_period_start",
    },
    {
      field: "step2.liabilitiesStart25",
      value: data.liabilities_total_period_start,
      label: t("dropzone_field_liabs_start"),
      sourceKey: "form1.liabilities_total_period_start",
    },
  ];
  for (const entry of ca037Hidden) {
    if (entry.value === null || entry.value === "") continue;
    setValue(entry.field, normalizeDigits(entry.value), {
      shouldValidate: true,
    });
    filled.push({
      fieldLabel: entry.label,
      sourceLabel: data.source_trail[entry.sourceKey] ?? sourceAutofill,
    });
  }

  return filled;
}

function normalizeDigits(decimalStr: string): string {
  // Decimal как "5973686000" или "5973686000.00" → "5973686000".
  // Отрицательные (убытки) обрезаем до 0 — форма UZS требует positive digits-only.
  // Отрицательные net_profit отображаются через другие KPI (margin), для form
  // оставляем 0 с подписью в сводке.
  if (decimalStr.startsWith("-")) return "0";
  const dot = decimalStr.indexOf(".");
  return dot >= 0 ? decimalStr.slice(0, dot) : decimalStr;
}
