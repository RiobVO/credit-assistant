"use client";

import { CheckCircle2, AlertCircle, TriangleAlert, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type {
  DossierResponseDto,
  RedFlagDto,
  Recommendation,
  Severity,
} from "@/lib/api";

const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  approve: "Одобрить",
  review: "На дополнительную проверку",
  reject: "Отказ",
};

const RECOMMENDATION_PALETTE: Record<
  Recommendation,
  { tone: string; chip: string; dot: string }
> = {
  approve: {
    tone: "text-[var(--ca-success)]",
    chip: "bg-[var(--ca-success-50)] border-[#BFE2D2] text-[var(--ca-success)]",
    dot: "bg-[var(--ca-success)]",
  },
  review: {
    tone: "text-[var(--ca-warning)]",
    chip: "bg-[#FFF6E5] border-[#F1D9A6] text-[var(--ca-warning)]",
    dot: "bg-[var(--ca-warning)]",
  },
  reject: {
    tone: "text-[var(--ca-danger)]",
    chip: "bg-[#FCE7E5] border-[#F2BCBA] text-[var(--ca-danger)]",
    dot: "bg-[var(--ca-danger)]",
  },
};

const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const SEVERITY_PALETTE: Record<Severity, { chip: string; icon: React.ReactNode }> = {
  low: {
    chip: "bg-[var(--ca-success-50)] border-[#BFE2D2] text-[var(--ca-success)]",
    icon: <CheckCircle2 className="size-3.5" />,
  },
  medium: {
    chip: "bg-[#FFF6E5] border-[#F1D9A6] text-[var(--ca-warning)]",
    icon: <AlertCircle className="size-3.5" />,
  },
  high: {
    chip: "bg-[#FCE7E5] border-[#F2BCBA] text-[var(--ca-danger)]",
    icon: <TriangleAlert className="size-3.5" />,
  },
  critical: {
    chip: "bg-[var(--ca-danger)]/10 border-[var(--ca-danger)] text-[var(--ca-danger)]",
    icon: <XCircle className="size-3.5" />,
  },
};

export function DossierResult({
  data,
  onNew,
}: {
  data: DossierResponseDto;
  onNew: () => void;
}) {
  const palette = RECOMMENDATION_PALETTE[data.risk_score.recommendation];
  const breakdown = data.risk_score.severity_breakdown;

  return (
    <div className="space-y-[18px]">
      <section className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
        <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
          <div>
            <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
              Сводная оценка
            </h2>
            <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
              ИНН {data.borrower_inn_masked} · скоринг на {data.as_of} ·{" "}
              {data.rules_evaluated} правил проверено
            </p>
          </div>
          <span
            className={cn(
              "ml-auto inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12.5px] font-semibold",
              palette.chip,
            )}
          >
            <span className={cn("size-1.5 rounded-full", palette.dot)} />
            {RECOMMENDATION_LABEL[data.risk_score.recommendation]}
          </span>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-[260px_1fr]">
          <div className="flex flex-col items-center justify-center gap-2 border-r border-[#EFF1F5] bg-gradient-to-b from-[#FAFBFC] to-white px-[22px] py-7">
            <div className="text-[10.5px] font-semibold tracking-[1.2px] text-[var(--ca-ink-400)] uppercase">
              Risk score
            </div>
            <div
              className={cn(
                "font-mono text-[56px] leading-none font-bold tracking-[-2px]",
                palette.tone,
              )}
            >
              {data.risk_score.score}
            </div>
            <div className="font-mono text-[11px] text-[var(--ca-ink-400)]">
              из 100 · &lt;15 одобрить · 15-29 проверить · ≥30 отказ
            </div>
          </div>

          <div className="grid grid-cols-2 gap-[18px] px-[26px] py-[22px] md:grid-cols-4">
            <BreakdownCell
              label="Critical"
              value={breakdown.critical ?? 0}
              tone="critical"
            />
            <BreakdownCell label="High" value={breakdown.high ?? 0} tone="high" />
            <BreakdownCell
              label="Medium"
              value={breakdown.medium ?? 0}
              tone="medium"
            />
            <BreakdownCell label="Low" value={breakdown.low ?? 0} tone="low" />
          </div>
        </div>
      </section>

      <section className="rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] shadow-[0_1px_2px_rgba(16,24,40,0.05)]">
        <header className="flex items-center gap-2.5 border-b border-[var(--ca-border)] px-[22px] py-[18px]">
          <div>
            <h2 className="m-0 text-[15px] font-semibold text-[var(--ca-ink-900)]">
              Сработавшие красные флаги
            </h2>
            <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ca-ink-500)]">
              {data.red_flags.length === 0
                ? "Ни одно из 17 правил не сработало — заёмщик чист по проверенным критериям."
                : `Сработало ${data.red_flags.length} ${pluralFlags(data.red_flags.length)}`}
            </p>
          </div>
        </header>

        {data.red_flags.length === 0 ? (
          <div className="px-[22px] py-10 text-center text-[13px] text-[var(--ca-ink-500)]">
            <CheckCircle2 className="mx-auto mb-3 size-8 text-[var(--ca-success)]" />
            Все проверки пройдены.
          </div>
        ) : (
          <ul className="divide-y divide-[var(--ca-border)]">
            {data.red_flags.map((f) => (
              <RedFlagItem key={`${f.rule_id}-${f.detected_at}`} flag={f} />
            ))}
          </ul>
        )}
      </section>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onNew}
          className="inline-flex h-[38px] items-center gap-2 rounded-md border border-[var(--ca-border-strong)] bg-[var(--ca-surface)] px-4 text-[13.5px] font-semibold text-[var(--ca-ink-700)] hover:bg-[#FAFBFC]"
        >
          Новая заявка
        </button>
      </div>
    </div>
  );
}

function BreakdownCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: Severity;
}) {
  const palette = SEVERITY_PALETTE[tone];
  return (
    <div className="rounded-lg border border-dashed border-[var(--ca-border-strong)] bg-[#FAFBFC] px-3 py-3.5">
      <div className="flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.6px] text-[var(--ca-ink-500)] uppercase">
        <span className={cn("inline-flex size-4 items-center justify-center rounded", palette.chip)}>
          {palette.icon}
        </span>
        {label}
      </div>
      <div className="mt-1.5 font-mono text-[26px] leading-none font-semibold tracking-[-1px] text-[var(--ca-ink-900)]">
        {value}
      </div>
    </div>
  );
}

function RedFlagItem({ flag }: { flag: RedFlagDto }) {
  const palette = SEVERITY_PALETTE[flag.severity];
  return (
    <li className="px-[22px] py-3.5">
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-px text-[11px] font-semibold whitespace-nowrap",
            palette.chip,
          )}
        >
          {palette.icon}
          {SEVERITY_LABEL[flag.severity]}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
            <span className="font-mono text-[12px] font-semibold text-[var(--ca-ink-900)]">
              {flag.rule_id}
            </span>
            <span className="font-mono text-[11px] text-[var(--ca-ink-400)]">
              v{flag.rule_version}
            </span>
          </div>
          <p className="mt-1 text-[13px] text-[var(--ca-ink-700)]">
            {flag.message}
          </p>
          <p className="mt-1.5 text-[11.5px] text-[var(--ca-ink-400)]">
            <span className="font-medium">Источник:</span> {flag.source}
          </p>
          {Object.keys(flag.evidence).length > 0 ? (
            <details className="mt-2 text-[12px] text-[var(--ca-ink-500)]">
              <summary className="cursor-pointer font-medium select-none">
                Свидетельства
              </summary>
              <pre className="mt-1.5 max-h-48 overflow-auto rounded-md border border-[var(--ca-border)] bg-[#FAFBFC] p-2 font-mono text-[11.5px] text-[var(--ca-ink-700)]">
                {JSON.stringify(flag.evidence, null, 2)}
              </pre>
            </details>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function pluralFlags(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "правил";
  if (mod10 === 1) return "правило";
  if (mod10 >= 2 && mod10 <= 4) return "правила";
  return "правил";
}
