export function PageHead({ caseId }: { caseId: string | null }) {
  return (
    <div className="mb-6 flex items-start gap-6">
      <div>
        <h1 className="m-0 mb-1.5 text-[22px] font-semibold tracking-[-0.2px] text-[var(--ca-ink-900)]">
          Новая заявка на кредитную оценку
        </h1>
        <p className="m-0 text-[13.5px] text-[var(--ca-ink-500)]">
          Заполните данные о заёмщике для последующего скоринга и анализа риска.
        </p>
      </div>

      <div className="ml-auto flex items-center gap-[10px] rounded-lg border border-[var(--ca-border)] bg-[var(--ca-surface)] px-3 py-2">
        <span className="size-1.5 rounded-full bg-[var(--ca-warning)]" />
        <div>
          <div className="text-[11px] tracking-[0.6px] text-[var(--ca-ink-400)] uppercase">
            Дело
          </div>
          <div className="font-mono text-[13px] text-[var(--ca-ink-900)]">
            {caseId ?? "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
