"use client";

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { BrandProvider, type BrandClient } from "@/lib/brand-context";

export function Providers({
  brand,
  children,
}: {
  brand: BrandClient;
  children: ReactNode;
}) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <BrandProvider brand={brand}>{children}</BrandProvider>
    </QueryClientProvider>
  );
}
