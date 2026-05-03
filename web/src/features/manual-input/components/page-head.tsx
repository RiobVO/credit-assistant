"use client";

import { useTranslations } from "next-intl";

export function PageHead({ caseId }: { caseId: string | null }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="mb-6 flex items-start gap-6">
      <div>
        <h1 className="m-0 mb-1.5 text-[22px] font-semibold tracking-[-0.2px] text-[var(--ink-1)]">
          {t("page_head_title")}
        </h1>
        <p className="m-0 text-[13.5px] text-[var(--ink-3)]">
          {t("page_head_subtitle")}
        </p>
      </div>

      <div className="ml-auto flex items-center gap-[10px] rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
        <span className="size-1.5 rounded-full bg-[var(--state-warn-fg)]" />
        <div>
          <div className="text-[11px] tracking-[0.6px] text-[var(--ink-4)] uppercase">
            {t("case_label")}
          </div>
          <div className="font-mono text-[13px] text-[var(--ink-1)]">
            {caseId ?? "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
