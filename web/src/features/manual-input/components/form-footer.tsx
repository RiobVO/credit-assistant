import { Loader2, MoveLeft, MoveRight, Save, Send } from "lucide-react";
import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

type Variant = "step1" | "step2" | "step3";

const NEXT_LABEL: Record<Variant, string> = {
  step1: "Далее: финансовые показатели",
  step2: "Далее: параметры кредита",
  step3: "Отправить на скоринг",
};

export function FormFooter({
  variant,
  onCancel,
  onBack,
  onNext,
  onSaveDraft,
  isSubmitting = false,
  isNextDisabled = false,
}: {
  variant: Variant;
  onCancel?: () => void;
  onBack?: () => void;
  onNext?: () => void;
  onSaveDraft?: () => void;
  isSubmitting?: boolean;
  isNextDisabled?: boolean;
}) {
  const showBack = variant !== "step1";
  const showCancel = variant === "step1";

  return (
    <div className="mt-[22px] flex items-center gap-3 rounded-[10px] border border-[var(--ca-border)] bg-[var(--ca-surface)] px-[18px] py-[14px]">
      <div className="flex items-center gap-2 text-[12.5px] text-[var(--ca-ink-500)]">
        <span className="size-1.5 rounded-full bg-[var(--ca-ink-400)]" />
        Черновик не сохранён локально
      </div>

      <div className="ml-auto flex gap-[10px]">
        {showCancel ? (
          <FootButton variant="ghost" onClick={onCancel}>
            Отменить
          </FootButton>
        ) : null}

        {showBack ? (
          <FootButton variant="ghost" onClick={onBack}>
            <MoveLeft className="size-4" /> Назад
          </FootButton>
        ) : null}

        <FootButton variant="ghost" onClick={onSaveDraft}>
          <Save className="size-4" /> Сохранить как черновик
        </FootButton>

        <FootButton
          variant="primary"
          onClick={onNext}
          disabled={isNextDisabled || isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Отправка…
            </>
          ) : (
            <>
              {variant === "step3" ? <Send className="size-4" /> : null}
              {NEXT_LABEL[variant]}
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
          "border-[var(--ca-border-strong)] bg-[var(--ca-surface)] text-[var(--ca-ink-700)] hover:bg-[#FAFBFC] disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "border-[var(--ca-primary-blue)] bg-[var(--ca-primary-blue)] text-white hover:border-[var(--ca-primary-blue-700)] hover:bg-[var(--ca-primary-blue-700)] disabled:cursor-not-allowed disabled:border-[#A8BDE2] disabled:bg-[#A8BDE2] disabled:text-[#EAF0FB]",
      )}
    >
      {children}
    </button>
  );
}
