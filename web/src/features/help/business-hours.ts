// CA-DS7: расписание hotline — из brand-config (опционально), fallback на
// 09-18 Asia/Tashkent. Tenant-aware: разные банки могут иметь разные часы
// работы поддержки. ``schedule`` приходит из ``useBrand().businessHours``
// в HelpView; null/undefined — берём default. Минутная гранулярность
// сейчас обрезается до часа (HH:MM → H) — для smoke достаточно; полная
// поддержка минут потребует i18n update (``hour`` → ``time``).

import type { BrandBusinessHours } from "@/lib/brand";

export type HotlineStatus =
  | { open: true; untilHour: number }
  | { open: false; opensAtHour: number };

const DEFAULT_SCHEDULE: BrandBusinessHours = {
  timezone: "Asia/Tashkent",
  weekdays: { start: "09:00", end: "18:00" },
};

function hourOf(hhmm: string): number {
  const [h] = hhmm.split(":");
  const parsed = parseInt(h ?? "0", 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function getParts(now: Date, tz: string): { weekday: number; hour: number } {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short",
    hour: "2-digit",
    hour12: false,
  });
  const parts = fmt.formatToParts(now);
  const weekdayStr = parts.find((p) => p.type === "weekday")?.value ?? "Sun";
  const hourStr = parts.find((p) => p.type === "hour")?.value ?? "0";
  const wdMap: Record<string, number> = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
  };
  return {
    weekday: wdMap[weekdayStr] ?? 0,
    hour: parseInt(hourStr, 10) % 24,
  };
}

export function getHotlineStatus(
  now: Date,
  schedule?: BrandBusinessHours | null,
): HotlineStatus {
  const cfg = schedule ?? DEFAULT_SCHEDULE;
  const { weekday, hour } = getParts(now, cfg.timezone);
  const openHour = hourOf(cfg.weekdays.start);
  const closeHour = hourOf(cfg.weekdays.end);
  const isWeekday = weekday >= 1 && weekday <= 5;
  if (isWeekday && hour >= openHour && hour < closeHour) {
    return { open: true, untilHour: closeHour };
  }
  return { open: false, opensAtHour: openHour };
}
