// Static-locale i18n: один язык на инсталляцию через NEXT_PUBLIC_LOCALE
// (по умолчанию "ru"). Без runtime-switcher — узбекская локаль для
// инсталляций в банках где интерфейс должен быть на uz.
//
// CA-063 / ADR-0011: keyspace разделён на shared/bank/accountant/dossier,
// чтобы mode-specific переводы не конфликтовали.

import ru from "./ru.json";
import uz from "./uz.json";

export type Locale = "ru" | "uz";

const MESSAGES: Record<Locale, typeof ru> = { ru, uz };

export const DEFAULT_LOCALE: Locale = "ru";

export function resolveLocale(raw: string | undefined): Locale {
  if (raw === "uz") return "uz";
  return DEFAULT_LOCALE;
}

export function getMessages(locale: Locale): typeof ru {
  return MESSAGES[locale];
}
