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
import { useRef, useState } from "react";
import { type FieldPath, useFormContext } from "react-hook-form";

import { ApiError, type ParsedFinancialsDto, parseManualInputFiles } from "@/lib/api";
import { cn } from "@/lib/utils";

import type { FormValues } from "../_schema";

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
  const { setValue } = useFormContext<FormValues>();
  const [files, setFiles] = useState<File[]>([]);
  const [autofilled, setAutofilled] = useState<Source[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: () => parseManualInputFiles(files),
    onSuccess: (data) => {
      const filled = applyToForm(data, setValue);
      setAutofilled(filled);
      setWarnings(data.parse_warnings ?? []);
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
      ? formatApiError(mutation.error)
      : mutation.error
        ? "Не удалось распарсить файлы"
        : null;

  return (
    <section className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
        <Upload className="size-4 text-[var(--ca-primary-blue)]" />
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
            Автозаполнение из выгрузок my3.soliq.uz
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
            Загрузите xltx-файлы (Форма №2, декларация НДС) — поля ниже заполнятся
            автоматически. Можно несколько за один год / разные годы.
          </p>
        </div>
      </header>

      <div className="space-y-4 p-[22px]">
        <DropZone
          onSelect={onAddFiles}
          inputRef={inputRef}
        />

        {files.length > 0 && (
          <ul className="divide-y divide-[var(--ca-border)] rounded-md border border-[var(--ca-border)]">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-2 px-3 py-2">
                <FileText className="size-4 flex-none text-[var(--ca-ink-400)]" />
                <span className="flex-1 truncate text-[13px] text-[var(--ca-ink-700)]">
                  {f.name}
                </span>
                <span className="font-mono text-[11.5px] text-[var(--ca-ink-400)]">
                  {(f.size / 1024).toFixed(0)} КБ
                </span>
                <button
                  type="button"
                  aria-label={`Удалить ${f.name}`}
                  onClick={() => removeFile(i)}
                  className="rounded p-1 text-[var(--ca-ink-400)] transition-colors hover:bg-[#FCE7E5] hover:text-[var(--ca-danger)]"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center justify-between">
          <span className="text-[12px] text-[var(--ca-ink-500)]">
            {files.length === 0
              ? `До ${MAX_FILES} файлов · xltx из личного кабинета Soliq`
              : `${files.length} ${pluralFiles(files.length)} готов${files.length === 1 ? "" : "ы"} к загрузке`}
          </span>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => mutation.mutate()}
            className={cn(
              "inline-flex h-[38px] items-center gap-2 rounded-md px-5 text-[13.5px] font-semibold transition-colors",
              canSubmit
                ? "bg-[var(--ca-primary-blue)] text-white hover:bg-[var(--ca-primary-blue-700)]"
                : "cursor-not-allowed bg-[#E5E9EF] text-[var(--ca-ink-400)]",
            )}
          >
            {mutation.isPending ? "Парсим…" : "Распарсить и заполнить"}
          </button>
        </div>

        {errorMessage && (
          <div className="flex items-start gap-2 rounded-md border border-[#F2BCBA] bg-[#FCE7E5] px-3 py-2 text-[12.5px] text-[var(--ca-danger)]">
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
          ? "border-[var(--ca-primary-blue)] bg-[#F4F8FF]"
          : "border-[var(--ca-border-strong)] bg-[#FAFBFC] hover:bg-[#F4F6F9]",
      )}
    >
      <Upload className="size-5 text-[var(--ca-ink-500)]" />
      <span className="text-[13px] font-medium text-[var(--ca-ink-700)]">
        Перетащите xltx-файлы сюда
      </span>
      <span className="text-[11.5px] text-[var(--ca-ink-500)]">
        или нажмите, чтобы выбрать (несколько файлов сразу)
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
  return (
    <div className="rounded-md border border-[#BFE2D2] bg-[var(--ca-success-50)] px-3 py-2.5">
      <div className="mb-1.5 flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--ca-success)]">
        <CheckCircle2 className="size-4" />
        Автозаполнено {entries.length} {pluralFields(entries.length)}
      </div>
      <ul className="space-y-1 text-[12px] text-[var(--ca-ink-700)]">
        {entries.map((e, i) => (
          <li key={i} className="flex items-baseline gap-2">
            <span className="font-medium">{e.fieldLabel}</span>
            {e.year ? <span className="text-[var(--ca-ink-500)]">{e.year}</span> : null}
            <span className="text-[11.5px] text-[var(--ca-ink-500)]">— из {e.sourceLabel}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WarningsBlock({ warnings }: { warnings: string[] }) {
  return (
    <details className="rounded-md border border-[#F1D9A6] bg-[#FFF6E5] px-3 py-2">
      <summary className="cursor-pointer text-[12.5px] font-semibold text-[var(--ca-warning)]">
        Предупреждения парсера ({warnings.length})
      </summary>
      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-[11.5px] text-[var(--ca-ink-700)]">
        {warnings.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
      </ul>
    </details>
  );
}

function formatApiError(err: ApiError): string {
  if (typeof err.body === "object" && err.body !== null && "detail" in err.body) {
    return String((err.body as { detail: unknown }).detail);
  }
  return `Запрос завершился ошибкой ${err.status}`;
}

function pluralFiles(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "файлов";
  if (mod10 === 1) return "файл";
  if (mod10 >= 2 && mod10 <= 4) return "файла";
  return "файлов";
}

function pluralFields(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "полей";
  if (mod10 === 1) return "поле";
  if (mod10 >= 2 && mod10 <= 4) return "поля";
  return "полей";
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
): Source[] {
  const filled: Source[] = [];

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
      data.source_trail[`revenue_${year}`] ?? "файл",
      "Выручка (годовой total)",
    );
  }
  for (const [year, value] of Object.entries(data.net_profit_by_year)) {
    setAnnual(
      "netProfit",
      Number(year),
      value,
      data.source_trail[`net_profit_${year}`] ?? "файл",
      "Чистая прибыль (годовой total)",
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
      fieldLabel: "НДС задекларированный (за 2025 г.)",
      sourceLabel: data.source_trail["vat_declared_2025"] ?? "файл",
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
