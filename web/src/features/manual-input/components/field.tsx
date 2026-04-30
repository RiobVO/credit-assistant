import { type ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Field({
  label,
  required,
  help,
  error,
  children,
  className,
  badge,
}: {
  label: string;
  required?: boolean;
  help?: ReactNode;
  error?: string;
  children: ReactNode;
  className?: string;
  badge?: ReactNode;
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <div className="flex items-center gap-1.5">
        <label className="text-[13px] font-medium text-[var(--ink-2)]">
          {label}{" "}
          {required ? (
            <span className="font-semibold text-[var(--state-bad-fg)]">*</span>
          ) : null}
        </label>
        {badge}
      </div>
      {children}
      {error ? (
        <div className="text-[12px] text-[var(--state-bad-fg)]">{error}</div>
      ) : help ? (
        <div className="mt-0.5 text-[12px] text-[var(--ink-4)]">{help}</div>
      ) : null}
    </div>
  );
}

const inputBase =
  "h-[38px] w-full rounded-md border border-[var(--border-strong)] bg-[var(--surface)] px-3 text-[14px] text-[var(--ink-1)] outline-none transition-colors placeholder:text-[#9BA3B3] focus:border-[var(--brand-primary)] focus:shadow-[0_0_0_3px_rgba(30,85,201,0.15)]";

export const fieldInputClass = inputBase;

export function FieldInput({
  invalid,
  className,
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      {...rest}
      aria-invalid={invalid || undefined}
      className={cn(
        inputBase,
        invalid &&
          "border-[var(--state-bad-fg)] focus:border-[var(--state-bad-fg)] focus:shadow-[0_0_0_3px_rgba(180,35,24,0.15)]",
        className,
      )}
    />
  );
}

export function InputGroup({
  children,
  addon,
}: {
  children: ReactNode;
  addon: ReactNode;
}) {
  return (
    <div className="flex items-stretch">
      <div className="[&>input]:rounded-r-none [&>input]:border-r-0 [&>div>input]:rounded-r-none [&>div>input]:border-r-0 flex-1">
        {children}
      </div>
      <div className="grid place-items-center rounded-r-md border border-l-0 border-[var(--border-strong)] bg-[#FAFBFC] px-3 text-[var(--ink-3)]">
        {addon}
      </div>
    </div>
  );
}
