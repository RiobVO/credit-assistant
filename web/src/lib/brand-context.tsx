"use client";

import { createContext, useContext, type ReactNode } from "react";

export type BrandClient = {
  id: string;
  name: string;
  tagline: string;
  logoMark: string;
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
