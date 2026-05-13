"use client";

import { useTranslations } from "next-intl";

// Phase 2 (DS-PHASE-2): live-strip pill «● Сегодня · 247 досье · 84% одобрено
// · 12 в проверке».
//
// TODO[CA-DS-LIVE]: цифры сейчас mock — нужен backend endpoint
// `/api/bank/stats/today` (cron-aggregated daily metrics). Pilot-demo папа
// видит placeholder; реальные метрики — отдельный sprint.

const MOCK = { collected: 247, approved_pct: 84, in_review: 12 };

export function LiveStrip() {
  const t = useTranslations("bank.search");
  return (
    <div className="mb-8 inline-flex animate-[rise_0.55s_cubic-bezier(0.16,0.84,0.44,1)_0.16s_both] items-center gap-4 rounded-full border border-[var(--border)] bg-white/55 px-3.5 py-2 text-[12px] text-[var(--ink-3)] backdrop-blur">
      <span className="inline-flex items-center gap-1.5 text-[10.5px] font-semibold tracking-[0.08em] text-[var(--ink-4)] uppercase">
        <span
          aria-hidden
          className="pulse-ring-ok size-1.5 rounded-full"
          style={{ background: "var(--state-ok-fg)" }}
        />
        {t("live_label")}
      </span>
      <span className="inline-flex items-baseline gap-1.5">
        <span className="font-mono text-[13px] font-semibold tabular-nums text-[var(--ink-1)]">
          {MOCK.collected}
        </span>
        {t("live_collected")}
      </span>
      <span className="h-3 w-px bg-[var(--border)]" aria-hidden />
      <span className="inline-flex items-baseline gap-1.5">
        <span className="font-mono text-[13px] font-semibold tabular-nums text-[var(--ink-1)]">
          {MOCK.approved_pct}%
        </span>
        {t("live_approved")}
      </span>
      <span className="h-3 w-px bg-[var(--border)]" aria-hidden />
      <span className="inline-flex items-baseline gap-1.5">
        <span className="font-mono text-[13px] font-semibold tabular-nums text-[var(--ink-1)]">
          {MOCK.in_review}
        </span>
        {t("live_in_review")}
      </span>
    </div>
  );
}
