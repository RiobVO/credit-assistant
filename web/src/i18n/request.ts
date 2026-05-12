// next-intl server-side config. Использует static LOCALE из env
// (один UI-язык на инсталляцию, без routing-switcher).

import { getRequestConfig } from "next-intl/server";

import { LOCALE } from "@/lib/config";
import { getMessages, resolveLocale } from ".";

export default getRequestConfig(async () => {
  const locale = resolveLocale(LOCALE);
  return {
    locale,
    messages: getMessages(locale),
  };
});
