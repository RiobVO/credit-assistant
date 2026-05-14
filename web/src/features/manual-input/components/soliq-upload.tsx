"use client";

// Карточка «Сверить НДС с ЭСФ»: пара xltx (Расчёт НДС + ilova-приложение №4) →
// POST /api/upload/soliq-xltx → preview → step2.vatPeriod в форме. При финальном
// submit уйдёт в payload.vat_periods[0].
//
// Phase 7 polish: section card pattern Phase 6 (icon-tile + gradient header),
// custom dropdowns для year/month вместо native <select> (premium-bank tone),
// semantic tokens вместо hex, h-40/rounded-[9px] на кнопках.

import { useMutation } from "@tanstack/react-query";
import {
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  Trash2,
  TriangleAlert,
  Upload,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { ApiError, uploadSoliqXltx } from "@/lib/api";
import { cn } from "@/lib/utils";

import { CustomDropdown } from "./custom-dropdown";
import { formatUzs } from "../lib/finance";
import { getYearsRange } from "../lib/years";
import type { FormValues, VatPeriodFromSoliq } from "../schema";

const MONTH_KEYS = [
  "soliq_month_jan",
  "soliq_month_feb",
  "soliq_month_mar",
  "soliq_month_apr",
  "soliq_month_may",
  "soliq_month_jun",
  "soliq_month_jul",
  "soliq_month_aug",
  "soliq_month_sep",
  "soliq_month_oct",
  "soliq_month_nov",
  "soliq_month_dec",
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
  const t = useTranslations("accountant.manual_input");
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
    !innMissing &&
    files.length === 2 &&
    month >= 1 &&
    month <= 12 &&
    !mutation.isPending;

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

  const monthOptions = MONTH_KEYS.map((mk, idx) => ({
    value: idx + 1,
    label: t(mk),
  }));
  const yearOptions = YEARS.map((y) => ({ value: y, label: String(y) }));

  return (
    <section className="overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)]">
      <header className="grid grid-cols-[40px_1fr_auto] items-center gap-[14px] border-b border-[var(--border)] bg-gradient-to-b from-white to-[var(--surface-2)] px-[22px] py-[16px]">
        <div className="grid size-9 place-items-center rounded-[10px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]">
          <FileSpreadsheet className="size-[18px]" />
        </div>
        <div>
          <h2 className="m-0 text-[15px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
            {t("soliq_title")}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {t("soliq_sub")}
          </p>
        </div>
        {field.value ? (
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-[8px] border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-1.5 text-[12px] text-[var(--ink-2)] transition-colors hover:bg-[var(--surface-2)]"
          >
            <Trash2 className="size-3.5" />
            {t("soliq_reset")}
          </button>
        ) : (
          <div />
        )}
      </header>

      <div className="space-y-4 p-[22px]">
        {field.value ? (
          <PreviewBlock data={field.value} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <FilePicker
                inputRef={declarationRef}
                label={t("soliq_file_1_label")}
                hint={t("soliq_file_1_hint")}
                file={files[0] ?? null}
                onChange={(f) => onAddFile(f)}
                onRemove={() => removeFile(0)}
              />
              <FilePicker
                inputRef={ilovaRef}
                label={t("soliq_file_2_label")}
                hint={t("soliq_file_2_hint")}
                file={files[1] ?? null}
                onChange={(f) => onAddFile(f)}
                onRemove={() => removeFile(1)}
              />
            </div>

            <div className="grid grid-cols-1 items-end gap-3 md:grid-cols-3">
              <CustomDropdown
                label={t("soliq_year_label")}
                value={year}
                onChange={setYear}
                options={yearOptions}
              />
              <CustomDropdown
                label={t("soliq_month_label")}
                value={month}
                onChange={setMonth}
                options={monthOptions}
              />
              <button
                type="button"
                disabled={!canSubmit}
                onClick={() => mutation.mutate()}
                className={cn(
                  "h-[40px] rounded-[9px] px-4 text-[13.5px] font-semibold transition-colors",
                  canSubmit
                    ? "bg-[var(--brand-primary)] text-white shadow-[0_4px_14px_-5px_var(--brand-primary)] hover:bg-[var(--brand-primary-hover)]"
                    : "cursor-not-allowed bg-[var(--surface-2)] text-[var(--ink-4)]",
                )}
              >
                {mutation.isPending ? t("soliq_submitting") : t("soliq_submit")}
              </button>
            </div>

            {innMissing ? (
              <Hint tone="warn" text={t("soliq_inn_missing_hint")} />
            ) : files.length < 2 ? (
              <Hint tone="info" text={t("soliq_two_files_hint")} />
            ) : null}

            {mutation.isError ? <ErrorBlock error={mutation.error} /> : null}
          </>
        )}
      </div>
    </section>
  );
}

// ─────────── FilePicker ──────────────────────────────────────────────────

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
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      className={cn(
        "flex flex-col gap-2.5 rounded-[11px] border border-dashed p-4 transition-colors",
        file
          ? "border-[var(--state-ok-border)] bg-gradient-to-b from-[var(--state-ok-bg)]/40 to-white"
          : "border-[var(--border-strong)] bg-[var(--surface-2)]",
      )}
    >
      <div
        className={cn(
          "text-[10.5px] font-bold tracking-[0.08em] uppercase",
          file ? "text-[var(--state-ok-fg)]" : "text-[var(--ink-3)]",
        )}
      >
        {label}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div className="flex items-center justify-between gap-3 rounded-[8px] border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-[var(--ink-3)]" />
            <span className="truncate text-[13px] text-[var(--ink-2)]">
              {file.name}
            </span>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="text-[12px] text-[var(--state-bad-fg)] hover:underline"
          >
            {t("soliq_remove_file")}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full items-center justify-center gap-2 rounded-[9px] border border-[var(--border-strong)] bg-[var(--surface)] py-2.5 text-[13px] text-[var(--ink-2)] transition-colors hover:border-[var(--brand-primary)] hover:bg-[var(--brand-primary-soft)] hover:text-[var(--brand-primary-ink)]"
        >
          <Upload className="size-4" />
          {t("soliq_pick_file")}
        </button>
      )}
      <div className="text-[11.5px] text-[var(--ink-4)]">{hint}</div>
    </div>
  );
}

// ─────────── Preview block (после успешного parse) ───────────────────────

function PreviewBlock({ data }: { data: VatPeriodFromSoliq }) {
  const t = useTranslations("accountant.manual_input");
  const monthLabel = t(MONTH_KEYS[data.month - 1]);
  const diffOk = data.diffPct
    ? Number(String(data.diffPct).replace("%", "").replace(",", ".")) <= 15
    : null;

  return (
    <div className="space-y-2.5">
      <div className="flex items-start gap-2.5 rounded-[10px] border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] px-[14px] py-3">
        <CheckCircle2 className="mt-px size-4 flex-none text-[var(--state-ok-fg)]" />
        <div className="text-[13px] leading-[1.5] text-[var(--ink-1)]">
          <b className="font-semibold">
            {t("soliq_preview_recognized", {
              month: monthLabel.toLowerCase(),
              year: data.year,
            })}
          </b>{" "}
          {data.organizationName ? (
            <span className="text-[var(--ink-3)]">{data.organizationName}</span>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
        <Stat
          label={t("soliq_stat_vat_decl")}
          value={`${formatUzs(integerPart(data.vatDeclared))} UZS`}
        />
        <Stat
          label={t("soliq_stat_esf")}
          value={`${formatUzs(integerPart(data.esfSellerVat))} UZS`}
        />
        <Stat
          label={t("soliq_stat_diff")}
          value={data.diffPct ?? "—"}
          tone={diffOk === null ? "neutral" : diffOk ? "good" : "warn"}
        />
      </div>

      {data.submittedAt ? (
        <div className="text-[12px] text-[var(--ink-4)]">
          {t("soliq_submitted_at", { date: data.submittedAt })}
        </div>
      ) : null}

      <ParseWarnings
        warnings={data.parseWarnings ?? []}
        skipped={data.skippedRowsCount ?? 0}
      />
    </div>
  );
}

function ParseWarnings({
  warnings,
  skipped,
}: {
  warnings: string[];
  skipped: number;
}) {
  const t = useTranslations("accountant.manual_input");
  const [open, setOpen] = useState(false);
  if (warnings.length === 0 && skipped === 0) return null;

  const total = warnings.length;
  const summary =
    skipped > 0
      ? t("soliq_warnings_with_skipped", { count: total, skipped })
      : t("soliq_warnings_summary", { count: total });

  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}
      className="rounded-[10px] border border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] px-[14px] py-2.5"
    >
      <summary className="cursor-pointer list-none text-[12.5px] font-medium text-[var(--ink-2)]">
        <span
          className="mr-1 inline-block transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          ▸
        </span>
        {summary}
      </summary>
      {warnings.length > 0 ? (
        <ul className="mt-2 space-y-1 text-[12px] leading-[1.5] text-[var(--ink-2)]">
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
    <div className="rounded-[11px] border border-dashed border-[var(--border-strong)] bg-[var(--surface-2)] px-[14px] py-3">
      <div className="text-[12px] tracking-[0.6px] text-[var(--ink-3)] uppercase">
        {label}
      </div>
      <div
        className={cn(
          "mt-1 font-mono text-[14px] font-semibold",
          tone === "good" && "text-[var(--state-ok-fg)]",
          tone === "warn" && "text-[var(--state-warn-fg)]",
          tone === "neutral" && "text-[var(--ink-1)]",
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
        "rounded-[10px] border px-[14px] py-2.5 text-[12.5px]",
        tone === "info" &&
          "border-[var(--border)] bg-[var(--surface-2)] text-[var(--ink-3)]",
        tone === "warn" &&
          "border-[var(--state-warn-border)] bg-[var(--state-warn-bg)] text-[var(--ink-2)]",
      )}
    >
      {text}
    </div>
  );
}

function ErrorBlock({ error }: { error: unknown }) {
  const t = useTranslations("accountant.manual_input");
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
    message = t("soliq_generic_error");
  }
  return (
    <div className="flex items-start gap-2.5 rounded-[10px] border border-[var(--state-bad-border)] bg-[var(--state-bad-bg)] px-[14px] py-3">
      <TriangleAlert className="mt-px size-4 flex-none text-[var(--state-bad-fg)]" />
      <div className="text-[13px] leading-[1.5] text-[var(--state-bad-fg)]">
        {message}
      </div>
    </div>
  );
}

function integerPart(amount: string): string {
  const i = amount.indexOf(".");
  return i === -1 ? amount : amount.slice(0, i);
}
