"use client";

// CA-DS29: runtime UI-language switcher для topbar. Compact CustomDropdown
// (RU / UZ), смена → server action → revalidate layout → новый RSC render
// с messages свежей локали. Без page reload.
//
// Pending state через useTransition — disable interactions пока action
// в flight (~100мс на revalidate). Custom dropdown сам не имеет disabled
// prop, поэтому оборачиваем родителя в opacity/pointer-events.

import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { setLocaleAction } from "@/app/_actions/set-locale";
import { CustomDropdown } from "@/features/manual-input/components/custom-dropdown";
import type { Locale } from "@/i18n";
import { LOCALE_VALUES } from "@/lib/locale-cookie";
import { cn } from "@/lib/utils";

export function LocaleSwitcher() {
  const t = useTranslations("shared.topbar");
  const current = useLocale() as Locale;
  const [pending, startTransition] = useTransition();

  const options = LOCALE_VALUES.map((v) => ({
    value: v,
    label: t(`locale_${v}`),
  }));

  return (
    <div
      role="group"
      aria-label={t("locale_switcher_aria")}
      className={cn(
        "min-w-[78px] transition-opacity",
        pending && "pointer-events-none opacity-60",
      )}
    >
      <CustomDropdown<Locale>
        value={current}
        options={options}
        onChange={(next) => {
          if (next === current) return;
          startTransition(() => {
            void setLocaleAction(next);
          });
        }}
      />
    </div>
  );
}
