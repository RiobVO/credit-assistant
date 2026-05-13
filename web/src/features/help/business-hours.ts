export type HotlineStatus =
  | { open: true; untilHour: number }
  | { open: false; opensAtHour: number };

const TZ = "Asia/Tashkent";
const OPEN_HOUR = 9;
const CLOSE_HOUR = 18;

function getTashkentParts(now: Date): { weekday: number; hour: number } {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
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

export function getHotlineStatus(now: Date): HotlineStatus {
  const { weekday, hour } = getTashkentParts(now);
  const isWeekday = weekday >= 1 && weekday <= 5;
  if (isWeekday && hour >= OPEN_HOUR && hour < CLOSE_HOUR) {
    return { open: true, untilHour: CLOSE_HOUR };
  }
  return { open: false, opensAtHour: OPEN_HOUR };
}
