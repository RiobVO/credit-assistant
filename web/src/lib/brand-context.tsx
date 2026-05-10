"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { BrandBusinessHours, BrandSupport } from "./brand";

export type BrandClient = {
  id: string;
  name: string;
  tagline: string;
  logoMark: string;
  // CA-DS6/7/8: support (контакты для /help) + businessHours (расписание
  // hotline). null если секция в brand-config отсутствует — HelpView сам
  // решит как рендерить (placeholder / hide).
  support: BrandSupport | null;
  businessHours: BrandBusinessHours | null;
};

const BrandContext = createContext<BrandClient | null>(null);

export function BrandProvider({
  brand,
  children,
}: {
  brand: BrandClient;
  children: ReactNode;
}) {
  return <BrandContext.Provider value={brand}>{children}</BrandContext.Provider>;
}

export function useBrand(): BrandClient {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error("useBrand must be used within BrandProvider");
  return ctx;
}
