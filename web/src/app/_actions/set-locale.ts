"use server";

// CA-DS29: server action для записи cookie + revalidate. Вызывается из
// LocaleSwitcher client component через useTransition. Не доступен из API
// — это RSC mutation, не HTTP endpoint.

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import type { Locale } from "@/i18n";
import {
  LOCALE_COOKIE,
  LOCALE_COOKIE_MAX_AGE_SEC,
  LOCALE_VALUES,
} from "@/lib/locale-cookie";

export async function setLocaleAction(locale: string): Promise<void> {
  if (!LOCALE_VALUES.includes(locale as Locale)) return;
  const store = await cookies();
  store.set(LOCALE_COOKIE, locale, {
    path: "/",
    sameSite: "lax",
    maxAge: LOCALE_COOKIE_MAX_AGE_SEC,
    // НЕ httpOnly: client-side LocaleSwitcher должен видеть current locale
    // через useLocale() (next-intl) → подгружается из request, но cookie
    // нужен для optimistic preview в будущем. Никаких credentials.
    httpOnly: false,
    // secure в production (HTTPS-only). В localhost разрешаем http.
    secure: process.env.NODE_ENV === "production",
  });
  // Revalidate всех серверных компонентов под root layout — i18n RSC
  // получит новую локаль на следующем рендере.
  revalidatePath("/", "layout");
}
