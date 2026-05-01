import { type ReactNode } from "react";

// Шапка экрана: h1 28px + опциональный sub-текст + опциональный actions row.
// Mockup: `.page-head { gap: 6px; margin-bottom: var(--s-7); }`.
export function BankPageHead({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-[28px] font-semibold leading-tight tracking-[-0.02em] text-[var(--ink-1)]">
          {title}
        </h1>
        {subtitle ? (
          <p className="m-0 max-w-[70ch] text-[15px] text-[var(--ink-3)]">
            {subtitle}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </header>
  );
}
