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

export function Stepper({ activeStep }: { activeStep: StepIdx }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      role="progressbar"
      aria-valuenow={activeStep}
      aria-valuemin={1}
      aria-valuemax={3}
      className="relative mb-5 grid grid-cols-3 gap-0 rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-[14px]"
    >
      {[1, 2, 3].map((idx) => {
        const isActive = idx === activeStep;
        const isDone = idx < activeStep;
        const title = t(STEP_TITLE_KEYS[idx - 1]);
        return (
          <div
            key={idx}
            className="relative flex items-center gap-3 px-[10px] py-1.5"
          >
            <div
              className={cn(
                "z-[1] grid size-7 flex-none place-items-center rounded-full border text-[13px] font-semibold",
                isDone &&
                  "border-[var(--state-ok-fg)] bg-[var(--state-ok-fg)] text-white",
                isActive &&
                  "border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white",
                !isActive &&
                  !isDone &&
                  "border-[var(--border)] bg-[var(--surface)] text-[var(--ink-3)]",
              )}
            >
              {isDone ? <Check className="size-3.5" /> : idx}
            </div>
            <div className="flex flex-col leading-[1.2]">
              <span
                className={cn(
                  "text-[11px] tracking-[0.6px] uppercase",
                  isActive
                    ? "text-[var(--brand-primary)]"
                    : "text-[var(--ink-4)]",
                )}
              >
                {t("stepper_step_prefix", { n: idx })}
                {isDone ? ` · ${t("stepper_done_suffix")}` : ""}
              </span>
              <span
                className={cn(
                  "mt-0.5 text-[13.5px] font-semibold",
                  isActive
                    ? "text-[var(--ink-1)]"
                    : "text-[var(--ink-2)]",
                )}
              >
                {title}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
