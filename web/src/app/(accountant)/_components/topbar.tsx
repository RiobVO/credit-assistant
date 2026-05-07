import { Bell, HelpCircle, Search } from "lucide-react";
import { Fragment, type ReactNode } from "react";

export type Crumb = {
  label: string;
  current?: boolean;
};

export function Topbar({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <div className="flex items-center gap-[14px] border-b border-[var(--ca-border)] bg-[var(--ca-surface)] px-8 py-[14px]">
      <div className="text-[13px] text-[var(--ca-ink-500)]">
        {crumbs.map((c, i) => (
          <Fragment key={i}>
            {i > 0 ? (
              <span className="mx-2 text-[var(--ca-ink-400)]">/</span>
            ) : null}
            {c.current ? (
              <b className="font-semibold text-[var(--ca-ink-900)]">{c.label}</b>
            ) : (
              <span className="text-[var(--ca-ink-400)]">{c.label}</span>
            )}
          </Fragment>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <SearchBox />
        <IconButton title="Уведомления">
          <Bell className="size-4" />
        </IconButton>
        <IconButton title="Помощь">
          <HelpCircle className="size-4" />
        </IconButton>
      </div>
    </div>
  );
}

function SearchBox() {
  return (
    <div className="flex h-[34px] w-[280px] items-center gap-2 rounded-md border border-[var(--ca-border)] bg-white px-[10px] text-[var(--ca-ink-400)]">
      <Search className="size-4" />
      <input
        placeholder="Поиск по ИНН, заявкам…"
        className="flex-1 bg-transparent text-[var(--ca-ink-900)] outline-none placeholder:text-[var(--ca-ink-400)]"
      />
      <span className="rounded border border-[var(--ca-border)] bg-[#FAFBFC] px-[5px] py-px font-mono text-[10.5px] text-[var(--ca-ink-400)]">
        ⌘K
      </span>
    </div>
  );
}

function IconButton({ title, children }: { title: string; children: ReactNode }) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      className="grid size-[34px] place-items-center rounded-md border border-[var(--ca-border)] bg-white text-[var(--ca-ink-500)] transition-colors hover:bg-[#FAFBFC] hover:text-[var(--ca-ink-700)]"
    >
      {children}
    </button>
  );
}
