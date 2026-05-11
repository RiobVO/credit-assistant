"use client";

import { Coins, Info, ListOrdered } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode } from "react";

type Variant = "registry" | "financials" | "final";

const ICONS: Record<Variant, ReactNode> = {
  registry: <Info className="size-[16px]" />,
  financials: <ListOrdered className="size-[16px]" />,
  final: <Coins className="size-[16px]" />,
};

const KEYS: Record<Variant, { bold: string; body: string }> = {
  registry: { bold: "info_registry_bold", body: "info_registry_body" },
  financials: { bold: "info_financials_bold", body: "info_financials_body" },
  final: { bold: "info_final_bold", body: "info_final_body" },
};

// Phase 6: leading icon-tile pattern (как Phase 4 FAQ rows). Tile в
// rgba(white,0.55) внутри state-info-bg — выглядит как «вырезанная»
// плашка с прозрачной подложкой.
export function InfoBanner({ variant }: { variant: Variant }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div
      className="mb-[18px] grid grid-cols-[36px_1fr] items-center gap-[14px] rounded-[12px] border bg-[var(--state-info-bg)] px-4 py-3 text-[var(--state-info-fg)]"
      style={{
        borderColor: "color-mix(in srgb, var(--state-info-fg) 22%, transparent)",
      }}
    >
      <div className="grid size-8 place-items-center rounded-[9px] bg-[var(--surface)]/55 text-[var(--brand-primary-ink)]">
        {ICONS[variant]}
      </div>
      <div className="text-[13px] leading-[1.55]">
        <b className="font-bold">{t(KEYS[variant].bold)}</b>{" "}
        {t(KEYS[variant].body)}
      </div>
    </div>
  );
}
