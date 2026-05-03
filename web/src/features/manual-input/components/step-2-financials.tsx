"use client";

import { useTranslations } from "next-intl";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { cn } from "@/lib/utils";

import {
  computeDebtToAssets,
  computeEquity,
  digitsOnly,
  formatUzs,
  parseAmount,
} from "../lib/finance";
import type { FormValues } from "../schema";

import { Field, fieldInputClass } from "./field";
import { FinancialTable } from "./financial-table";
import { ParsedFilesDropzone } from "./parsed-files-dropzone";
import { SoliqUpload } from "./soliq-upload";

export function Step2Financials() {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="space-y-[18px]">
      <ParsedFilesDropzone />

      <SoliqUpload />

      <Card title={t("s2_revenue_title")} sub={t("s2_revenue_sub")}>
        <FinancialTable basePath="step2.revenue" variant="revenue" />
      </Card>

      <Card title={t("s2_profit_title")} sub={t("s2_profit_sub")}>
        <FinancialTable basePath="step2.netProfit" variant="netProfit" />
      </Card>

      <Card title={t("s2_annual_title")} sub={t("s2_annual_sub")}>
        <AnnualFields />
      </Card>
    </div>
  );
}

function Card({
  title,
  sub,
  children,
}: {
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[10px] border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
      <header className="flex items-center gap-2.5 border-b border-[var(--border)] px-[22px] py-[18px]">
        <div>
          <h2 className="m-0 text-[15px] font-semibold text-[var(--ink-1)]">
            {title}
          </h2>
          <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
            {sub}
          </p>
        </div>
      </header>
      <div className="p-[22px]">{children}</div>
    </section>
  );
}

function AnnualFields() {
  const t = useTranslations("accountant.manual_input");
  const {
    control,
    formState: { errors, touchedFields },
  } = useFormContext<FormValues>();

  const e = errors.step2;
  const touched = touchedFields.step2;

  return (
    <div className="space-y-[18px]">
      <div>
        <div className="mb-2 text-[12.5px] font-medium text-[var(--ink-2)]">
          {t("s2_taxes_heading")}
        </div>
        <p className="m-0 mb-2 text-[11.5px] text-[var(--ink-3)]">
          {t("s2_taxes_hint")}
        </p>
        <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-3">
          <UzsField
            name="step2.taxesPaid23"
            label={t("s2_taxes_y23_label")}
            help={t("s2_taxes_y23_help")}
            error={touched?.taxesPaid23 ? e?.taxesPaid23?.message : undefined}
          />
          <UzsField
            name="step2.taxesPaid24"
            label={t("s2_taxes_y24_label")}
            help={t("s2_taxes_y24_help")}
            error={touched?.taxesPaid24 ? e?.taxesPaid24?.message : undefined}
          />
          <UzsField
            name="step2.taxesPaid25"
            label={t("s2_taxes_y25_label")}
            help={t("s2_taxes_y25_help")}
            error={touched?.taxesPaid25 ? e?.taxesPaid25?.message : undefined}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-x-5 gap-y-[18px] md:grid-cols-2">
        <UzsField
          name="step2.vatDeclared"
          label={t("s2_vat_label")}
          help={t("s2_vat_help")}
          error={touched?.vatDeclared ? e?.vatDeclared?.message : undefined}
        />
        <UzsField
          name="step2.totalAssets"
          label={t("s2_assets_label")}
          help={t("s2_assets_help")}
          error={touched?.totalAssets ? e?.totalAssets?.message : undefined}
        />
        <UzsField
          name="step2.totalLiabilities"
          label={t("s2_liabs_label")}
          help={t("s2_liabs_help")}
          error={touched?.totalLiabilities ? e?.totalLiabilities?.message : undefined}
        />

        <ComputedRow control={control} />
      </div>
    </div>
  );
}

type UzsFieldName =
  | "step2.vatDeclared"
  | "step2.taxesPaid23"
  | "step2.taxesPaid24"
  | "step2.taxesPaid25"
  | "step2.totalAssets"
  | "step2.totalLiabilities";

function UzsField({
  name,
  label,
  help,
  error,
}: {
  name: UzsFieldName;
  label: string;
  help: string;
  error?: string;
}) {
  const { control } = useFormContext<FormValues>();
  return (
    <Field label={label} required help={help} error={error}>
      <div className="flex items-stretch">
        <Controller
          control={control}
          name={name}
          render={({ field }) => (
            <input
              ref={field.ref}
              value={formatUzs((field.value as string) ?? "")}
              onBlur={field.onBlur}
              onChange={(e) => field.onChange(digitsOnly(e.target.value))}
              inputMode="numeric"
              placeholder="0"
              aria-invalid={Boolean(error) || undefined}
              className={cn(
                fieldInputClass,
                "rounded-r-none border-r-0 text-right font-mono",
                error &&
                  "border-[var(--state-bad-fg)] focus:border-[var(--state-bad-fg)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
              )}
            />
          )}
        />
        <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[#FAFBFC] px-3 text-[13px] text-[var(--ink-3)]">
          UZS
        </div>
      </div>
    </Field>
  );
}

function ComputedRow({
  control,
}: {
  control: import("react-hook-form").Control<FormValues>;
}) {
  const t = useTranslations("accountant.manual_input");
  const assets = useWatch({ control, name: "step2.totalAssets" });
  const liabilities = useWatch({ control, name: "step2.totalLiabilities" });

  const a = parseAmount(assets ?? "");
  const l = parseAmount(liabilities ?? "");
  const da = computeDebtToAssets(l, a);
  const equity = computeEquity(a, l);

  return (
    <div className="md:col-span-2">
      <ComputedBox
        keyLabel={t("s2_da_label")}
        sub={t("s2_da_sub")}
        value={a === 0 ? "—" : da.toFixed(2)}
        tone="neutral"
      />
      <div className="h-2.5" />
      <ComputedBox
        keyLabel={t("s2_equity_label")}
        sub={t("s2_equity_sub")}
        value={equity > 0 ? `${formatUzs(String(equity))} UZS` : "—"}
        tone="neutral"
      />
    </div>
  );
}

function ComputedBox({
  keyLabel,
  sub,
  value,
  tone,
}: {
  keyLabel: string;
  sub: string;
  value: string;
  tone: "good" | "warn" | "neutral";
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-dashed border-[var(--border-strong)] bg-[#FAFBFC] px-[14px] py-3">
      <div>
        <div className="text-[12px] tracking-[0.6px] text-[var(--ink-3)] uppercase">
          {keyLabel}
        </div>
        <div className="mt-0.5 text-[12px] text-[var(--ink-4)]">{sub}</div>
      </div>
      <div
        className={cn(
          "font-mono text-[14px] font-semibold",
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
