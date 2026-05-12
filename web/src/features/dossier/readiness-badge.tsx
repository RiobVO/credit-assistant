"use client";

// CA-035b: Readiness badge для готового досье. Компактный pill с level
// (Insufficient/Minimal/Standard/Comprehensive) + confidence_score% +
// inline список missing_capabilities (если есть).
//
// Семантика дополняет, не дублирует ROE/Debt-to-EBIT карточки: KPI говорят
// «что мы посчитали», readiness — «насколько мы можем доверять расчётам».
// Аналитик видит, что досье построено на partial-данных и может запросить
// у клиента FORM_1 / ESF-выгрузку перед approve.

import { useQuery } from "@tanstack/react-query";
import { Check, Info, TriangleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { getDossierReadiness } from "@/lib/api";
import { cn } from "@/lib/utils";

type Status = "ok" | "warn" | "pending";

const LEVEL_KEY: Record<
  string,
  "level_insufficient" | "level_minimal" | "level_standard" | "level_comprehensive"
> = {
  insufficient: "level_insufficient",
  minimal: "level_minimal",
  standard: "level_standard",
  comprehensive: "level_comprehensive",
};

const LEVEL_STATUS: Record<string, Status> = {
  insufficient: "pending",
  minimal: "warn",
  standard: "warn",
  comprehensive: "ok",
};

const CAPABILITY_KEY: Record<
  string,
  | "capability_yoy_trend"
  | "capability_cagr"
  | "capability_balance_ratios"
  | "capability_tax_burden"
> = {
  yoy_trend: "capability_yoy_trend",
  cagr: "capability_cagr",
  balance_ratios: "capability_balance_ratios",
  tax_burden: "capability_tax_burden",
};

export function ReadinessBadge({ dossierId }: { dossierId: string }) {
  const t = useTranslations("dossier.readiness");
  const query = useQuery({
    queryKey: ["dossier-readiness", dossierId],
    queryFn: () => getDossierReadiness(dossierId),
    retry: 1,
    staleTime: 60_000,
  });

  // Тихо ничего не рендерим во время загрузки/ошибки: readiness — derived
  // signal, не блокирующая часть досье. Если бэк не отвечает — досье
  // остаётся читаемым, только без сигнала «доверие к данным».
  if (!query.data) return null;

  const data = query.data;
  const status = LEVEL_STATUS[data.level] ?? "warn";
  const Icon = status === "ok" ? Check : status === "pending" ? X : TriangleAlert;

  const palette = {
    ok: "border-[#BFE2D2] bg-[var(--state-ok-bg)] text-[var(--state-ok-fg)]",
    warn: "border-[#F1D9A6] bg-[#FFF6E5] text-[var(--state-warn-fg)]",
    pending: "border-[#F2BCBA] bg-[#FCE7E5] text-[var(--state-bad-fg)]",
  }[status];

  const levelKey = LEVEL_KEY[data.level];
  const levelLabel = levelKey ? t(levelKey) : data.level;
  const missing = data.missing_capabilities.map((c) => {
    const ck = CAPABILITY_KEY[c];
    return ck ? t(ck) : c;
  });

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span
        className={cn(
          "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[12.5px] font-medium",
          palette,
        )}
      >
        <Icon className="size-3.5" />
        {t("pill_template", {
          level: levelLabel,
          confidence: formatConfidence(data.confidence_score),
        })}
      </span>
      {missing.length > 0 && (
        <span className="inline-flex items-center gap-1.5 text-[12px] text-[var(--ink-3)]">
          <Info className="size-3.5 text-[var(--state-warn-fg)]" />
          {t("missing_prefix", { items: missing.join(" · ") })}
        </span>
      )}
    </div>
  );
}

function formatConfidence(decimalStr: string): string {
  const n = Number.parseFloat(decimalStr);
  if (Number.isNaN(n)) return "—";
  return `${Math.round(n * 100)}%`;
}
