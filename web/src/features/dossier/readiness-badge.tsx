"use client";

// CA-035b → дизайн-парити: вместо отдельного pill — 4-я KPI-карточка
// «Готовность данных» в KpiRow. Семантика та же: «насколько мы можем
// доверять расчётам». Левая stripe по level (good/warn/bad), значение —
// confidence_score%, подзаголовок — LEVEL · источники.

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { getDossierReadiness } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tone = "good" | "warn" | "bad";

const LEVEL_KEY: Record<
  string,
  "level_insufficient" | "level_minimal" | "level_standard" | "level_comprehensive"
> = {
  insufficient: "level_insufficient",
  minimal: "level_minimal",
  standard: "level_standard",
  comprehensive: "level_comprehensive",
};

const LEVEL_TONE: Record<string, Tone> = {
  insufficient: "bad",
  minimal: "warn",
  standard: "warn",
  comprehensive: "good",
};

const SOURCE_KEY: Record<
  string,
  | "source_manual"
  | "source_form1"
  | "source_form2"
  | "source_vat_declaration"
  | "source_vat_registry_ilova"
  | "source_profit_tax"
  | "source_esf"
> = {
  manual: "source_manual",
  form1: "source_form1",
  form2: "source_form2",
  vat_declaration: "source_vat_declaration",
  vat_registry_ilova: "source_vat_registry_ilova",
  profit_tax: "source_profit_tax",
  esf: "source_esf",
};

const STRIPE_CLASS: Record<Tone, string> = {
  good: "border-l-4 border-l-[var(--state-ok-fg)]",
  warn: "border-l-4 border-l-[var(--state-warn-fg)]",
  bad: "border-l-4 border-l-[var(--state-bad-fg)]",
};

export function ReadinessKpiCard({
  dossierId,
  label,
}: {
  dossierId: string;
  label: string;
}) {
  const t = useTranslations("dossier.readiness");
  const query = useQuery({
    queryKey: ["dossier-readiness", dossierId],
    queryFn: () => getDossierReadiness(dossierId),
    retry: 1,
    staleTime: 60_000,
  });

  if (!query.data) {
    // Pending или error — non-blocking контракт CA-035b: KPI-row остаётся
    // читаемой, в карточке просто прочерк.
    return (
      <Card label={label} value="—" subtitle={query.isPending ? t("card_loading") : ""} />
    );
  }

  const data = query.data;
  const tone = LEVEL_TONE[data.level] ?? "warn";
  const levelKey = LEVEL_KEY[data.level];
  const levelLabel = (levelKey ? t(levelKey) : data.level).toUpperCase();
  const sources = data.parser_sources
    .map((s) => {
      const key = SOURCE_KEY[s];
      return key ? t(key) : s;
    })
    .join(" + ");
  const subtitle = sources ? `${levelLabel} · ${sources}` : levelLabel;

  return (
    <Card
      label={label}
      value={formatConfidence(data.confidence_score)}
      subtitle={subtitle}
      tone={tone}
    />
  );
}

function formatConfidence(decimalStr: string): string {
  const n = Number.parseFloat(decimalStr);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)} %`;
}

function Card({
  label,
  value,
  subtitle,
  tone,
}: {
  label: string;
  value: string;
  subtitle: string;
  tone?: Tone;
}) {
  return (
    <div
      className={cn(
        "rounded-[10px] border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_1px_2px_rgba(16,24,40,0.05)]",
        tone && STRIPE_CLASS[tone],
      )}
    >
      <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ink-4)] uppercase">
        {label}
      </div>
      <div className="mt-2 font-mono text-[24px] leading-none font-semibold tracking-[-0.6px] text-[var(--ink-1)]">
        {value}
      </div>
      <div className="mt-2 text-[11.5px] text-[var(--ink-3)]">
        {subtitle || " "}
      </div>
      <div className="mt-3 h-[36px]" aria-hidden="true" />
    </div>
  );
}
