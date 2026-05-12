import { z } from "zod";

import defaultJson from "../../../config/brands/default.json";
import uzbekbankJson from "../../../config/brands/uzbekbank.json";

const hex = z.string().regex(/^#[0-9A-Fa-f]{6}$/, "must be #RRGGBB");
const rgba = z
  .string()
  .regex(/^rgba\(\s*\d+,\s*\d+,\s*\d+,\s*[0-9.]+\)$/, "must be rgba(r,g,b,a)");

export const brandSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  tagline: z.string(),
  logoMark: z.string().min(1).max(4),
  primary: hex,
  primaryHover: hex,
  primarySoft: hex,
  primaryInk: hex,
  primaryRing: rgba,
});

export type BrandConfig = z.infer<typeof brandSchema>;

export type Brand = {
  id: string;
  name: string;
  tagline: string;
  logoMark: string;
  cssVars: Record<string, string>;
};

export function loadBrandFromJson(raw: unknown): Brand {
  const cfg = brandSchema.parse(raw);
  return {
    id: cfg.id,
    name: cfg.name,
    tagline: cfg.tagline,
    logoMark: cfg.logoMark,
    cssVars: {
      "--brand-primary": cfg.primary,
      "--brand-primary-hover": cfg.primaryHover,
      "--brand-primary-soft": cfg.primarySoft,
      "--brand-primary-ink": cfg.primaryInk,
      "--brand-primary-ring": cfg.primaryRing,
    },
  };
}

const REGISTRY: Record<string, Brand> = {
  default: loadBrandFromJson(defaultJson),
  uzbekbank: loadBrandFromJson(uzbekbankJson),
};

export function resolveBrand(brandId: string | undefined): Brand {
  if (brandId && REGISTRY[brandId]) return REGISTRY[brandId];
  return REGISTRY.default;
}
