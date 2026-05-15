// next-intl server-side config. Локаль резолвится в порядке приоритета:
//
//   1. ca_locale cookie — runtime switcher (CA-DS29). Пользователь явно
//      выбрал язык в topbar dropdown → действует до явной смены / истечения.
//   2. NEXT_PUBLIC_LOCALE env — installation default, build-time.
//   3. DEFAULT_LOCALE ("ru") — последний рубеж.

import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

import { LOCALE } from "@/lib/config";
import { LOCALE_COOKIE, readLocaleCookie } from "@/lib/locale-cookie";

import { getMessages, resolveLocale } from ".";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const cookieLocale = readLocaleCookie(cookieStore.get(LOCALE_COOKIE)?.value);
  const locale = cookieLocale ?? resolveLocale(LOCALE);
  return {
    locale,
    messages: getMessages(locale),
  };
});
