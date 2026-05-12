"use client";

import { Info, ListOrdered, Coins } from "lucide-react";
import { useTranslations } from "next-intl";
import { type ReactNode } from "react";

type Variant = "registry" | "financials" | "final";

const ICONS: Record<Variant, ReactNode> = {
  registry: <Info className="size-4" />,
  financials: <ListOrdered className="size-4" />,
  final: <Coins className="size-4" />,
};

const KEYS: Record<Variant, { bold: string; body: string }> = {
  registry: { bold: "info_registry_bold", body: "info_registry_body" },
  financials: { bold: "info_financials_bold", body: "info_financials_body" },
  final: { bold: "info_final_bold", body: "info_final_body" },
};

export function InfoBanner({ variant }: { variant: Variant }) {
  const t = useTranslations("accountant.manual_input");
  return (
    <div className="mb-[22px] flex items-start gap-3 rounded-lg border border-[#D4E1F7] bg-[#F4F8FF] px-[14px] py-3">
      <span className="mt-px flex-none text-[var(--brand-primary)]">
        {ICONS[variant]}
      </span>
      <div className="text-[13px] leading-[1.5] text-[#1A3A78]">
        <b className="text-[#0F2A5C]">{t(KEYS[variant].bold)}</b>
        {t(KEYS[variant].body)}
      </div>
    </div>
  );
}
