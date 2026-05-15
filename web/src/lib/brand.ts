import fs from "node:fs";
import path from "node:path";

import { z } from "zod";

const hex = z.string().regex(/^#[0-9A-Fa-f]{6}$/, "must be #RRGGBB");
const rgba = z
  .string()
  .regex(/^rgba\(\s*\d+,\s*\d+,\s*\d+,\s*[0-9.]+\)$/, "must be rgba(r,g,b,a)");
const hhmm = z.string().regex(/^\d{2}:\d{2}$/, "must be HH:MM");

// CA-DS6/7/8: support (контакты для /help) + businessHours (расписание hotline).
// Optional — brand-config без этих секций остаётся валидным; HelpView фолбэкается
// на «контакты не настроены» / «расписание не указано».
const supportSchema = z.object({
  phone: z.string().min(1),
  phoneTel: z.string().regex(/^tel:/, "must be tel:URI"),
  email: z.string().email(),
  slack: z.object({
    channel: z.string().min(1),
    workspace: z.string().min(1),
  }),
  docs: z.object({
    url: z.string().url(),
    label: z.string().min(1),
  }),
  compliancePhone: z.string().min(1),
});

const businessHoursSchema = z.object({
  timezone: z.string().min(1),
  weekdays: z.object({
    start: hhmm,
    end: hhmm,
  }),
});

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
  support: supportSchema.optional(),
  businessHours: businessHoursSchema.optional(),
});

export type BrandConfig = z.infer<typeof brandSchema>;
export type BrandSupport = z.infer<typeof supportSchema>;
export type BrandBusinessHours = z.infer<typeof businessHoursSchema>;

export type Brand = {
  id: string;
  name: string;
  tagline: string;
  logoMark: string;
  cssVars: Record<string, string>;
  support: BrandSupport | null;
  businessHours: BrandBusinessHours | null;
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
    support: cfg.support ?? null,
    businessHours: cfg.businessHours ?? null,
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
