import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { BRAND_ID, LOCALE } from "@/lib/config";
import { resolveBrand } from "@/lib/brand";
import { getMessages, resolveLocale } from "@/i18n";

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const brand = resolveBrand(BRAND_ID);
  const brandStyle = brand.cssVars as React.CSSProperties;
  const locale = resolveLocale(LOCALE);
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
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
