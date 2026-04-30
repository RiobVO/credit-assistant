import fs from "node:fs";
import path from "node:path";

import { z } from "zod";

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

function readBrandFile(brandId: string): Brand {
  const filePath = path.resolve(process.cwd(), "..", "config", "brands", `${brandId}.json`);
  const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  return loadBrandFromJson(raw);
}

const REGISTRY = new Map<string, Brand>();

export function resolveBrand(brandId: string | undefined): Brand {
  const id = brandId && /^[a-z0-9-]+$/.test(brandId) ? brandId : "default";
  const cached = REGISTRY.get(id);
  if (cached) return cached;
  try {
    const brand = readBrandFile(id);
    REGISTRY.set(id, brand);
    return brand;
  } catch {
    if (id !== "default") return resolveBrand("default");
    throw new Error(`Brand config missing: ${id}.json`);
  }
}
