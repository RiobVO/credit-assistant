"use client";

// Карточка «Загрузить из my3.soliq.uz»: пара xltx-файлов (Расчёт НДС +
// ilova-приложение №4) → POST /api/upload/soliq-xltx → preview →
// step2.vatPeriod в форме. При финальном submit уйдёт в payload.vat_periods[0].

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, FileText, Trash2, TriangleAlert, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { ApiError, uploadSoliqXltx } from "@/lib/api";
import { cn } from "@/lib/utils";

import { formatUzs } from "../_lib/finance";
import { getYearsRange } from "../_lib/years";
import type { FormValues, VatPeriodFromSoliq } from "../_schema";

const MONTHS_RU = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
] as const;

const YEARS = getYearsRange(15);
const ACCEPT = ".xltx,application/vnd.ms-excel.template.macroEnabled.12";

export function SoliqUpload() {
  const { control } = useFormContext<FormValues>();
  return (
    <Controller
      control={control}
      name="step2.vatPeriod"
      render={({ field }) => <SoliqUploadInner field={field} />}
    />
  );
}

type FieldShape = {
  value: VatPeriodFromSoliq | null;
  onChange: (v: VatPeriodFromSoliq | null) => void;
};

function SoliqUploadInner({ field }: { field: FieldShape }) {
  const { control } = useFormContext<FormValues>();
  const inn = useWatch({ control, name: "step1.inn" });

  const [files, setFiles] = useState<File[]>([]);
  const [year, setYear] = useState<number>(YEARS[0]);
  const [month, setMonth] = useState<number>(3);

  const declarationRef = useRef<HTMLInputElement>(null);
  const ilovaRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: () =>
      uploadSoliqXltx({
        files,
        borrowerInn: inn ?? "",
        periodMonth: month,
      }),
    onSuccess: (data) => {
      field.onChange({
        year,
        month,
        vatDeclared: data.vat_declared?.amount ?? "0",
        esfSellerVat: data.esf_seller_vat_total?.amount ?? "0",
        organizationName: data.organization_name ?? undefined,
        submittedAt: data.submitted_at ?? undefined,
        diffPct: data.diff_pct ?? undefined,
        parseWarnings: data.parse_warnings ?? [],
        skippedRowsCount: data.skipped_rows_count ?? 0,
      });
    },
  });

  const innMissing = !inn || !/^\d{9}$/.test(inn);
  const canSubmit =
    !innMissing && files.length === 2 && month >= 1 && month <= 12 && !mutation.isPending;

  const onAddFile = (file: File | null) => {
    if (!file) return;
    setFiles((prev) => {
      if (prev.length >= 2) return prev;
      if (prev.some((f) => f.name === file.name && f.size === file.size)) return prev;
      return [...prev, file];
    });
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
    mutation.reset();
  };

  const reset = () => {
    setFiles([]);
    field.onChange(null);
    mutation.reset();
    if (declarationRef.current) declarationRef.current.value = "";
    if (ilovaRef.current) ilovaRef.current.value = "";
  };

  return (
    <section className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-start justify-between gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
            Загрузить из my3.soliq.uz
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
            Расчёт НДС + ilova-приложение №4 за один налоговый период (один месяц)
          </p>
        </div>
        {field.value ? (
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-3 py-1.5 text-[12px] text-[var(--ca-ink-700)] transition-colors hover:bg-[#FAFBFC]"
          >
            <Trash2 className="size-3.5" />
            Сбросить
          </button>
        ) : null}
      </header>

      <div className="space-y-4 p-[22px]">
        {field.value ? (
          <PreviewBlock data={field.value} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <FilePicker
                inputRef={declarationRef}
                label="Файл 1"
                hint="Расчёт НДС или ilova"
                file={files[0] ?? null}
                onChange={(f) => onAddFile(f)}
                onRemove={() => removeFile(0)}
              />
              <FilePicker
                inputRef={ilovaRef}
                label="Файл 2"
                hint="Расчёт НДС или ilova"
                file={files[1] ?? null}
                onChange={(f) => onAddFile(f)}
                onRemove={() => removeFile(1)}
              />
            </div>

            <div className="grid grid-cols-1 items-end gap-3 md:grid-cols-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[13px] font-medium text-[var(--ca-ink-700)]">Год</label>
                <select
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className="h-[38px] rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-3 text-[14px] text-[var(--ca-ink-900)]"
                >
                  {YEARS.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[13px] font-medium text-[var(--ca-ink-700)]">Месяц</label>
                <select
                  value={month}
                  onChange={(e) => setMonth(Number(e.target.value))}
                  className="h-[38px] rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-3 text-[14px] text-[var(--ca-ink-900)]"
                >
                  {MONTHS_RU.map((label, idx) => (
                    <option key={idx} value={idx + 1}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                disabled={!canSubmit}
                onClick={() => mutation.mutate()}
                className={cn(
                  "h-[38px] rounded-md px-4 text-[13px] font-semibold transition-colors",
                  canSubmit
                    ? "bg-[var(--ca-primary-blue)] text-white hover:opacity-90"
                    : "cursor-not-allowed bg-[#E5E8EE] text-[var(--ca-ink-400)]",
                )}
              >
                {mutation.isPending ? "Распознаём…" : "Распознать"}
              </button>
            </div>

            {innMissing ? (
              <Hint
                tone="warn"
                text="Заполните ИНН на Шаге 1 — он нужен для проверки соответствия декларации."
              />
            ) : files.length < 2 ? (
              <Hint tone="info" text="Загрузите ровно два файла: декларацию и ilova-реестр." />
            ) : null}

            {mutation.isError ? <ErrorBlock error={mutation.error} /> : null}
          </>
        )}
      </div>
    </section>
  );
}

function FilePicker({
  inputRef,
  label,
  hint,
  file,
  onChange,
  onRemove,
}: {
  inputRef: React.RefObject<HTMLInputElement | null>;
  label: string;
  hint: string;
  file: File | null;
  onChange: (file: File | null) => void;
  onRemove: () => void;
}) {
  return (
    <div className="rounded-md border border-dashed border-[var(--ca-border-strong)] bg-[#FAFBFC] p-4">
      <div className="text-[12px] tracking-[0.4px] text-[var(--ca-ink-500)] uppercase">{label}</div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div className="mt-2 flex items-center justify-between gap-3 rounded-md border border-[var(--ca-border)] bg-[var(--ca-surface)] px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-[var(--ca-ink-500)]" />
            <span className="truncate text-[13px] text-[var(--ca-ink-700)]">{file.name}</span>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="text-[12px] text-[var(--ca-danger)] hover:underline"
          >
            Удалить
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-2 flex w-full items-center justify-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] py-3 text-[13px] text-[var(--ca-ink-700)] hover:bg-[#F4F6FA]"
        >
          <Upload className="size-4" />
          Выбрать .xltx
        </button>
      )}
      <div className="mt-1.5 text-[12px] text-[var(--ca-ink-400)]">{hint}</div>
    </div>
  );
}

function PreviewBlock({ data }: { data: VatPeriodFromSoliq }) {
  const monthLabel = MONTHS_RU[data.month - 1];
  const diffOk = data.diffPct
    ? Number(String(data.diffPct).replace("%", "").replace(",", ".")) <= 15
    : null;

  return (
    <div className="space-y-2.5">
      <div className="flex items-start gap-2.5 rounded-md border border-[#BFE7C8] bg-[#E9F7EE] px-[14px] py-3">
        <CheckCircle2 className="mt-px size-4 flex-none text-[var(--ca-success)]" />
        <div className="text-[13px] leading-[1.5] text-[var(--ca-ink-900)]">
          <b className="font-semibold">Распознан период {monthLabel.toLowerCase()} {data.year}.</b>{" "}
          {data.organizationName ? (
            <span className="text-[var(--ca-ink-500)]">{data.organizationName}</span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
        <Stat
          label="Декларация НДС"
          value={`${formatUzs(integerPart(data.vatDeclared))} UZS`}
        />
        <Stat
          label="Сумма НДС из ЭСФ"
          value={`${formatUzs(integerPart(data.esfSellerVat))} UZS`}
        />
        <Stat
          label="Расхождение"
          value={data.diffPct ?? "—"}
          tone={diffOk === null ? "neutral" : diffOk ? "good" : "warn"}
        />
      </div>

      {data.submittedAt ? (
        <div className="text-[12px] text-[var(--ca-ink-400)]">
          Дата подачи: {data.submittedAt}
        </div>
      ) : null}

      <ParseWarnings warnings={data.parseWarnings ?? []} skipped={data.skippedRowsCount ?? 0} />
    </div>
  );
}

function ParseWarnings({ warnings, skipped }: { warnings: string[]; skipped: number }) {
  const [open, setOpen] = useState(false);
  if (warnings.length === 0 && skipped === 0) return null;

  const total = warnings.length;
  const summary =
    skipped > 0
      ? `Предупреждения парсера (${total}) · пропущено строк: ${skipped}`
      : `Предупреждения парсера (${total})`;

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="rounded-md border border-[#F2DBA1] bg-[#FCF4DD] px-[14px] py-2.5"
    >
      <summary className="cursor-pointer list-none text-[12.5px] font-medium text-[var(--ca-ink-700)]">
        <span className="mr-1 inline-block transition-transform" style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}>▸</span>
        {summary}
      </summary>
      {warnings.length > 0 ? (
        <ul className="mt-2 space-y-1 text-[12px] leading-[1.5] text-[var(--ca-ink-700)]">
          {warnings.map((w, i) => (
            <li key={i} className="font-mono break-all">
              · {w}
            </li>
          ))}
        </ul>
      ) : null}
    </details>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "good" | "warn" | "neutral";
}) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--ca-border-strong)] bg-[#FAFBFC] px-[14px] py-3">
      <div className="text-[12px] tracking-[0.6px] text-[var(--ca-ink-500)] uppercase">{label}</div>
      <div
        className={cn(
          "mt-1 font-mono text-[14px] font-semibold",
          tone === "good" && "text-[var(--ca-success)]",
          tone === "warn" && "text-[var(--ca-warning)]",
          tone === "neutral" && "text-[var(--ca-ink-900)]",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function Hint({ tone, text }: { tone: "info" | "warn"; text: string }) {
  return (
    <div
      className={cn(
        "rounded-md border px-[14px] py-2.5 text-[12.5px]",
        tone === "info" &&
          "border-[var(--ca-border)] bg-[#F4F6FA] text-[var(--ca-ink-500)]",
        tone === "warn" &&
          "border-[#F2DBA1] bg-[#FCF4DD] text-[var(--ca-ink-700)]",
      )}
    >
      {text}
    </div>
  );
}

function ErrorBlock({ error }: { error: unknown }) {
  let message: string;
  if (error instanceof ApiError) {
    if (typeof error.body === "string") {
      message = error.body || `HTTP ${error.status}`;
    } else if (error.body?.detail && typeof error.body.detail === "string") {
      message = error.body.detail;
    } else {
      message = JSON.stringify(error.body);
    }
  } else if (error instanceof Error) {
    message = error.message;
  } else {
    message = "Не удалось распознать выгрузку";
  }
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-[#F2BCBA] bg-[#FCE7E5] px-[14px] py-3">
      <TriangleAlert className="mt-px size-4 flex-none text-[var(--ca-danger)]" />
      <div className="text-[13px] leading-[1.5] text-[var(--ca-danger)]">{message}</div>
    </div>
  );
}

function integerPart(amount: string): string {
  const i = amount.indexOf(".");
  return i === -1 ? amount : amount.slice(0, i);
}
