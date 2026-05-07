"use client";

import { useTranslations } from "next-intl";

// Phase 6: убрали warn-dot status-card (он подсознательно читался как
// «что-то не так»). Новый status-card по Phase 4 паттерну — пара chunks
// «● ЧЕРНОВИК · CR-...» + «ШАГ N из 3». Статичная зелёная точка, без
// pulse (банковский tone).
type StepIdx = 1 | 2 | 3;

export function PageHead({
  caseId,
  step,
}: {
  caseId: string | null;
  step: StepIdx;
}) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="mb-5 grid grid-cols-[1fr_auto] items-end gap-6">
      <div>
        <h1 className="m-0 text-[26px] font-semibold tracking-[-0.018em] leading-[1.15] text-[var(--ink-1)]">
          {t("page_head_title")}
        </h1>
        <p className="mt-1.5 text-[13.5px] text-[var(--ink-3)]">
          {t("page_head_subtitle")}
        </p>
      </div>

      <div className="inline-flex items-center gap-[14px] rounded-full border border-[var(--border)] bg-white/70 px-3.5 py-2.5 backdrop-blur-[8px]">
        <div className="inline-flex items-center gap-2 text-[11.5px] text-[var(--ink-2)]">
          <span className="size-1.5 rounded-full bg-[var(--state-ok-fg)]" />
          <div className="flex flex-col">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-4)]">
              {t("case_label")}
            </span>
            <span className="font-mono text-[12px] font-semibold text-[var(--ink-1)] tabular-nums">
              {caseId ?? "—"}
            </span>
          </div>
        </div>
        <div className="inline-flex items-center gap-2 border-l border-[var(--border)] pl-[14px] text-[11.5px] text-[var(--ink-2)]">
          <div className="flex flex-col">
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[var(--ink-4)]">
              {t("step_position_label")}
            </span>
            <span className="text-[12px] font-semibold text-[var(--ink-1)]">
              {t("step_position_value", { n: step, total: 3 })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
