"use client";

import { Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

type StepIdx = 1 | 2 | 3;

const STEP_TITLE_KEYS = [
  "stepper_step_1_title",
  "stepper_step_2_title",
  "stepper_step_3_title",
] as const;

// Phase 6 Step 1: connector между шагами убран — на active-шаге нет
// «прогресса позади», который мог бы быть нарисован, и серая линия для
// pending-шагов читалась как шум. 3 кружка с label'ами достаточно для
// orientation; «1/3» подкреплён status-card в PageHead (Phase 4 паттерн).
export function Stepper({ activeStep }: { activeStep: StepIdx }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      role="progressbar"
      aria-valuenow={activeStep}
      aria-valuemin={1}
      aria-valuemax={3}
      className="mb-5 rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[22px] py-[18px]"
    >
      <div className="grid grid-cols-3">
        {[1, 2, 3].map((idx) => {
          const isActive = idx === activeStep;
          const isDone = idx < activeStep;
          const isPending = !isActive && !isDone;
          const title = t(STEP_TITLE_KEYS[idx - 1]);
          const eyebrow = isActive
            ? t("stepper_step_active_eyebrow", { n: idx })
            : isDone
              ? t("stepper_step_done_eyebrow", { n: idx })
              : t("stepper_step_pending_eyebrow", { n: idx });
          return (
            <div
              key={idx}
              className="grid grid-cols-[36px_1fr] items-center gap-3 px-1"
            >
              <div
                className={cn(
                  "grid size-8 place-items-center rounded-full font-mono text-[13px] font-bold transition-colors",
                  isDone && "bg-[var(--state-ok-fg)] text-white",
                  isActive && "bg-[var(--brand-primary)] text-white",
                  isPending &&
                    "border-[1.5px] border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink-4)]",
                )}
              >
                {isDone ? <Check className="size-[14px]" /> : idx}
              </div>
              <div className="flex flex-col leading-[1.2]">
                <span
                  className={cn(
                    "text-[10.5px] font-semibold uppercase tracking-[0.09em]",
                    isActive && "text-[var(--brand-primary)]",
                    isDone && "text-[var(--state-ok-fg)]",
                    isPending && "text-[var(--ink-4)]",
                  )}
                >
                  {eyebrow}
                </span>
                <span
                  className={cn(
                    "mt-0.5 text-[13.5px] font-semibold",
                    isActive && "text-[var(--ink-1)]",
                    isDone && "text-[var(--ink-2)]",
                    isPending && "text-[var(--ink-3)]",
                  )}
                >
                  {title}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
