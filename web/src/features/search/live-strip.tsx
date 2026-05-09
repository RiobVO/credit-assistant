"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { fetchBankDailyStats } from "@/lib/bank-api";

// Phase 2 (DS-PHASE-2): live-strip pill «● Сегодня · N досье · M% одобрено
// · K в проверке». Данные из `/api/bank/stats/today` — реальная агрегация
// bank-mode dossiers за UTC-сегодня. При loading — skeleton-dashes
// «—», при error — тихо скрываем strip (не падаем UI).

export function LiveStrip() {
  const t = useTranslations("bank.search");
  const { data, isLoading, isError } = useQuery({
    queryKey: ["bank-stats-today"],
    queryFn: fetchBankDailyStats,
    staleTime: 60_000, // 1 мин — daily metric, refresh не критичен
    refetchOnWindowFocus: false,
  });

  if (isError) return null;

  const collected = isLoading || !data ? null : data.collected_today;
  const approvedPct = isLoading || !data ? null : data.approved_pct;
  const inReview = isLoading || !data ? null : data.in_review_today;

  return (
    <div className="mb-8 inline-flex animate-[rise_0.55s_cubic-bezier(0.16,0.84,0.44,1)_0.16s_both] items-center gap-4 rounded-full border border-[var(--border)] bg-white/55 px-3.5 py-2 text-[12px] text-[var(--ink-3)] backdrop-blur">
      <span className="inline-flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] text-[var(--ink-4)] uppercase">
        {/* CA-DS19: pulse убран — banking tone требует static индикаторы. */}
        <span
          aria-hidden
          className="size-1.5 rounded-full"
          style={{ background: "var(--state-ok-fg)" }}
        />
        {t("live_label")}
      </span>
      <Stat n={collected} label={t("live_collected")} />
      <span className="h-3 w-px bg-[var(--border)]" aria-hidden />
      <Stat n={approvedPct} label={t("live_approved")} pct />
      <span className="h-3 w-px bg-[var(--border)]" aria-hidden />
      <Stat n={inReview} label={t("live_in_review")} />
    </div>
  );
}

function Stat({ n, label, pct = false }: { n: number | null; label: string; pct?: boolean }) {
  const display = n === null ? "—" : pct ? `${n}%` : n.toLocaleString("ru-RU");
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="font-mono text-[13px] font-semibold tabular-nums text-[var(--ink-1)]">
        {display}
      </span>
      {label}
    </span>
  );
}
