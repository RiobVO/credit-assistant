// Section-card shell (Phase 6/7/8 pattern): icon-tile 36px + gradient header
// + optional aux slot (counter / static pill). Visual-only — без i18n bindings.
//
// Используется в Step 2 (Revenue / Profit / Annual), Step 3 (Loan params /
// DSCR / Checklist). Структура: grid [40px_1fr_auto] + 22px body padding.

import type { ReactNode } from "react";

export function SectionCard({
  icon,
  title,
  sub,
  aux,
  children,
}: {
  icon: ReactNode;
  title: ReactNode;
  sub?: ReactNode;
  aux?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)]">
      <header className="grid grid-cols-[40px_1fr_auto] items-center gap-[14px] border-b border-[var(--border)] bg-gradient-to-b from-white to-[var(--surface-2)] px-[22px] py-[16px]">
        <div className="grid size-9 place-items-center rounded-[10px] bg-[var(--brand-primary-soft)] text-[var(--brand-primary-ink)]">
          {icon}
        </div>
        <div>
          <h2 className="m-0 text-[15px] font-semibold tracking-[-0.005em] text-[var(--ink-1)]">
            {title}
          </h2>
          {sub ? (
            <p className="m-0 mt-0.5 text-[12.5px] text-[var(--ink-3)]">
              {sub}
            </p>
          ) : null}
        </div>
        {aux ?? <div />}
      </header>
      <div className="p-[22px]">{children}</div>
    </section>
  );
}

// Live progress counter «N/total» с eyebrow + 70px brand-primary progress bar.
// Когда filled === total — тон переключается на state-ok-fg (done).
export function CounterChip({
  filled,
  total,
  eyebrow,
}: {
  filled: number;
  total: number;
  eyebrow: ReactNode;
}) {
  const pct = total > 0 ? Math.min(100, Math.round((filled / total) * 100)) : 0;
  const done = filled >= total;
  const tone = done ? "var(--state-ok-fg)" : "var(--brand-primary)";
  return (
    <div className="text-right text-[11px] font-semibold tracking-[0.08em] text-[var(--ink-4)] uppercase">
      <div>{eyebrow}</div>
      <div className="mt-1 flex items-center gap-[6px]">
        <div className="relative h-1 w-[70px] overflow-hidden rounded-sm bg-[var(--surface-3)]">
          <div
            className="absolute inset-y-0 left-0 rounded-sm transition-[width] duration-200 ease-out"
            style={{ width: `${pct}%`, background: tone }}
          />
        </div>
        <span
          className="font-mono text-[11.5px] font-bold tracking-normal normal-case"
          style={{ color: tone }}
        >
          {filled}/{total}
        </span>
      </div>
    </div>
  );
}

// Static pill: dot + label. Для DSCR header «обновлено · {date}» без motion.
// Использует state-ok-fg как accent (semantic «всё в порядке, расчёт готов»).
export function StaticPill({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-[6px] rounded-full border border-[var(--state-ok-border)] bg-[var(--state-ok-bg)] px-[10px] py-[4px] text-[11px] font-medium text-[var(--state-ok-fg)]">
      <span
        aria-hidden
        className="size-[5px] rounded-full bg-[var(--state-ok-fg)]"
      />
      {children}
    </span>
  );
}
