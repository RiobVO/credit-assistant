"use client";

import { Loader2, MoveLeft, MoveRight, Send } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

type Variant = "step1" | "step2" | "step3";

const NEXT_KEY: Record<Variant, "footer_next_step1" | "footer_next_step2" | "footer_next_step3"> = {
  step1: "footer_next_step1",
  step2: "footer_next_step2",
  step3: "footer_next_step3",
};

// CA-057: «Сохранить как черновик» убрана — она была dead (onSaveDraft в
// manual-input-view не передавался, клик был no-op). Auto-save срабатывает
// в `goNext` на переходе между шагами — каноничный draft lifecycle.
// Индикатор «Сохранён в HH:MM» в Topbar информирует пользователя.
export function FormFooter({
  variant,
  onCancel,
  onBack,
  onNext,
  isSubmitting = false,
  isNextDisabled = false,
}: {
  variant: Variant;
  onCancel?: () => void;
  onBack?: () => void;
  onNext?: () => void;
  isSubmitting?: boolean;
  isNextDisabled?: boolean;
}) {
  const t = useTranslations("accountant.manual_input");
  const showBack = variant !== "step1";
  const showCancel = variant === "step1";

  return (
    <div className="mt-[22px] flex items-center gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-[14px]">
      <div className="flex items-center gap-2 text-[12.5px] text-[var(--ink-3)]">
        <span className="size-1.5 rounded-full bg-[var(--ink-4)]" />
        {t("footer_autosave_hint")}
      </div>

      <div className="ml-auto flex gap-[10px]">
        {showCancel ? (
          <FootButton variant="ghost" onClick={onCancel}>
            {t("footer_cancel")}
          </FootButton>
        ) : null}

        {showBack ? (
          <FootButton variant="ghost" onClick={onBack}>
            <MoveLeft className="size-4" /> {t("footer_back")}
          </FootButton>
        ) : null}

        <FootButton
          variant="primary"
          onClick={onNext}
          disabled={isNextDisabled || isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              {t("footer_submitting")}
            </>
          ) : (
            <>
              {variant === "step3" ? <Send className="size-4" /> : null}
              {t(NEXT_KEY[variant])}
              {variant !== "step3" ? <MoveRight className="size-4" /> : null}
            </>
          )}
        </FootButton>
      </div>
    </div>
  );
}

function FootButton({
  variant,
  children,
  onClick,
  disabled,
}: {
  variant: "ghost" | "primary";
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-[38px] items-center gap-2 rounded-md border px-4 text-[13.5px] font-semibold whitespace-nowrap transition-colors",
        variant === "ghost" &&
          "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--ink-2)] hover:bg-[#FAFBFC] disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white hover:border-[var(--brand-primary-hover)] hover:bg-[var(--brand-primary-hover)] disabled:cursor-not-allowed disabled:border-[#A8BDE2] disabled:bg-[#A8BDE2] disabled:text-[#EAF0FB]",
      )}
    >
      {children}
    </button>
  );
}
