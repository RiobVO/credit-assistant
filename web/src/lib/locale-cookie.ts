// CA-DS29: runtime locale switcher. Cookie-based persistence — пользователь
// меняет UI-язык через dropdown в topbar, выбор сохраняется в httpOnly=false
// cookie и читается на server при следующем request (RSC / layout).
//
// Cookie не httpOnly: клиентский JS должен видеть current locale без
// отдельного round-trip (для optimistic UI). Никаких credentials в cookie
// нет — это user preference, не auth.
//
// Fallback chain: cookie → NEXT_PUBLIC_LOCALE env → DEFAULT_LOCALE ("ru").

import type { Locale } from "@/i18n";
import { resolveLocale } from "@/i18n";

export const LOCALE_COOKIE = "ca_locale";

// 1 год — переключение редкое, явное действие пользователя.
export const LOCALE_COOKIE_MAX_AGE_SEC = 60 * 60 * 24 * 365;

export const LOCALE_VALUES = ["ru", "uz"] as const;

export function readLocaleCookie(value: string | undefined): Locale | null {
  if (value === undefined) return null;
  const resolved = resolveLocale(value);
  // resolveLocale возвращает DEFAULT_LOCALE для любой неизвестной строки;
  // мы хотим различать «cookie присутствует с валидной локалью» и
  // «cookie присутствует с мусором» (last case → null, fallback на env).
  return LOCALE_VALUES.includes(value as Locale) ? resolved : null;
}
