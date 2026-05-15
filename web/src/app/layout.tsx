import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { Inter, JetBrains_Mono } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";
import { BRAND_ID, LOCALE } from "@/lib/config";
import { resolveBrand } from "@/lib/brand";
import { getMessages, resolveLocale } from "@/i18n";
import { LOCALE_COOKIE, readLocaleCookie } from "@/lib/locale-cookie";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Credit Assistant — досье МСБ-заёмщика",
  description: "Внутренний инструмент банков для подготовки кредитного досье",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const brand = resolveBrand(BRAND_ID);
  const brandStyle = brand.cssVars as React.CSSProperties;
  // CA-DS29: locale из cookie если установлен, иначе env default. Чтение
  // sync через next/headers cookies() — RSC рендерится с правильным lang
  // attribute сразу, без client-side flash.
  const cookieStore = await cookies();
  const cookieLocale = readLocaleCookie(cookieStore.get(LOCALE_COOKIE)?.value);
  const locale = cookieLocale ?? resolveLocale(LOCALE);
  const messages = getMessages(locale);

  return (
    <html
      lang={locale}
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
      style={brandStyle}
      data-brand={brand.id}
    >
      <body className="min-h-full flex flex-col">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <Providers
            brand={{
              id: brand.id,
              name: brand.name,
              tagline: brand.tagline,
              logoMark: brand.logoMark,
              support: brand.support,
              businessHours: brand.businessHours,
            }}
          >
            {children}
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
